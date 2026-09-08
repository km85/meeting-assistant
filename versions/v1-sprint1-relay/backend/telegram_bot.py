import asyncio
import json
import time
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import get_settings
from session_manager import session_manager
from llm_handler import llm_handler

settings = get_settings()

# Latency tracking
latency_log: list[dict] = []


class TelegramBot:
    """Telegram bot for meeting assistant commands."""
    
    def __init__(self):
        self.app: Optional[Application] = None
    
    async def start(self):
        """Initialize and start the bot."""
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("assist", self.cmd_assist))
        self.app.add_handler(CommandHandler("say", self.cmd_say))
        self.app.add_handler(CommandHandler("followup", self.cmd_followup))
        self.app.add_handler(CommandHandler("recap", self.cmd_recap))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        print("Telegram bot started")
    
    async def stop(self):
        """Stop the bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
    
    async def send_message(self, text: str):
        """Send message to configured chat."""
        if self.app:
            await self.app.bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=text,
                parse_mode="Markdown"
            )
    
    # --- Command Handlers ---
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🎙️ *Meeting Assistant*\n\n"
            "Commands:\n"
            "• /assist — Real-time help\n"
            "• /say — Answer latest question\n"
            "• /followup — Suggest follow-up questions\n"
            "• /recap — Meeting summary\n"
            "• /stop — End session\n"
            "• /status — Check session status",
            parse_mode="Markdown"
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await self.cmd_start(update, context)
    
    async def cmd_assist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /assist command."""
        cmd_received = time.time()
        
        # Get active session (use first active or create default)
        active_sessions = session_manager.get_active_sessions()
        if not active_sessions:
            await update.message.reply_text(
                "❌ No active meeting session.\n"
                "Start listening on the Android app first."
            )
            return
        
        session_id = active_sessions[0]["session_id"]
        session = session_manager.get_session(session_id)
        
        # Generate response
        await update.message.reply_text("🤔 Analyzing context...")
        
        response = await llm_handler.generate_assist(session)
        
        # Log latency
        response_generated = time.time()
        telegram_sent = time.time()
        latency_log.append({
            "command": "assist",
            "command_received": cmd_received,
            "response_generated": response_generated,
            "telegram_sent": telegram_sent,
            "total_latency": telegram_sent - cmd_received,
        })
        
        await update.message.reply_text(
            f"💡 *Real-Time Assistance*\n\n{response}",
            parse_mode="Markdown"
        )
    
    async def cmd_say(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /say command."""
        cmd_received = time.time()
        
        active_sessions = session_manager.get_active_sessions()
        if not active_sessions:
            await update.message.reply_text(
                "❌ No active meeting session.\n"
                "Start listening on the Android app first."
            )
            return
        
        session_id = active_sessions[0]["session_id"]
        session = session_manager.get_session(session_id)
        
        await update.message.reply_text("🎯 Finding latest question...")
        
        response = await llm_handler.generate_say(session)
        
        response_generated = time.time()
        telegram_sent = time.time()
        latency_log.append({
            "command": "say",
            "command_received": cmd_received,
            "response_generated": response_generated,
            "telegram_sent": telegram_sent,
            "total_latency": telegram_sent - cmd_received,
        })
        
        await update.message.reply_text(
            f"🗣️ *Suggested Response*\n\n{response}",
            parse_mode="Markdown"
        )
    
    async def cmd_followup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /followup command."""
        cmd_received = time.time()
        
        active_sessions = session_manager.get_active_sessions()
        if not active_sessions:
            await update.message.reply_text(
                "❌ No active meeting session.\n"
                "Start listening on the Android app first."
            )
            return
        
        session_id = active_sessions[0]["session_id"]
        session = session_manager.get_session(session_id)
        
        await update.message.reply_text("🤔 Generating follow-up questions...")
        
        response = await llm_handler.generate_followup(session)
        
        response_generated = time.time()
        telegram_sent = time.time()
        latency_log.append({
            "command": "followup",
            "command_received": cmd_received,
            "response_generated": response_generated,
            "telegram_sent": telegram_sent,
            "total_latency": telegram_sent - cmd_received,
        })
        
        await update.message.reply_text(
            f"❓ *Follow-up Questions*\n\n{response}",
            parse_mode="Markdown"
        )
    
    async def cmd_recap(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recap command."""
        cmd_received = time.time()
        
        # Try to find any session (active or recently stopped)
        active_sessions = session_manager.get_active_sessions()
        
        session = None
        if active_sessions:
            session_id = active_sessions[0]["session_id"]
            session = session_manager.get_session(session_id)
        elif session_manager.sessions:
            # Get most recent session
            recent_sid = max(
                session_manager.sessions.keys(),
                key=lambda sid: session_manager.sessions[sid].last_activity
            )
            session = session_manager.get_session(recent_sid)
        
        if not session or not session.transcript:
            await update.message.reply_text(
                "❌ No meeting transcript available.\n"
                "Start listening on the Android app first."
            )
            return
        
        await update.message.reply_text("📝 Generating recap...")
        
        response = await llm_handler.generate_recap(session)
        
        response_generated = time.time()
        telegram_sent = time.time()
        latency_log.append({
            "command": "recap",
            "command_received": cmd_received,
            "response_generated": response_generated,
            "telegram_sent": telegram_sent,
            "total_latency": telegram_sent - cmd_received,
        })
        
        await update.message.reply_text(
            f"📊 *Meeting Recap*\n\n{response}",
            parse_mode="Markdown"
        )
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        active_sessions = session_manager.get_active_sessions()
        
        if not active_sessions:
            await update.message.reply_text("No active session to stop.")
            return
        
        for session_info in active_sessions:
            session_id = session_info["session_id"]
            session_manager.end_session(session_id)
        
        await update.message.reply_text(
            "🛑 *Meeting session stopped.*\n"
            "Temporary transcript cleared.\n\n"
            "Use /recap if you need the summary before it's gone."
        )
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        active_sessions = session_manager.get_active_sessions()
        
        if not active_sessions:
            await update.message.reply_text(
                "📵 *No active session*\n\n"
                "Status: Not listening\n"
                "Start the Android app to begin."
            )
            return
        
        session_info = active_sessions[0]
        duration = time.time() - session_info["created_at"]
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        await update.message.reply_text(
            f"🎙️ *Session Active*\n\n"
            f"Status: Listening\n"
            f"Duration: {minutes}m {seconds}s\n"
            f"Transcript entries: {session_info['transcript_count']}\n"
            f"Audio chunks: {session_info['metadata']['audio_chunks_received']}"
        )
    
    async def error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        print(f"Telegram error: {context.error}")
        if update and update.message:
            await update.message.reply_text(
                "⚠️ An error occurred. Please try again."
            )


# Global instance
telegram_bot = TelegramBot()
