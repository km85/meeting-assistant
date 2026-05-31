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

from app.config import get_settings
from app.session_manager import session_manager
from app.answer_generator import llm_handler
from app.security import log_audit, sanitize_log

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
        
        # Project commands (MVP)
        self.app.add_handler(CommandHandler("projects", self.cmd_projects))
        self.app.add_handler(CommandHandler("use_project", self.cmd_use_project))
        self.app.add_handler(CommandHandler("project_status", self.cmd_project_status))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        print("Telegram bot started")
        log_audit("telegram_bot_started")
    
    async def stop(self):
        """Stop the bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            log_audit("telegram_bot_stopped")
    
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
            "• /status — Check session status\n\n"
            "Project commands:\n"
            "• /projects — List projects\n"
            "• /use_project <name> — Set active project\n"
            "• /project_status — Check project status",
            parse_mode="Markdown"
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await self.cmd_start(update, context)
    
    async def cmd_assist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /assist command."""
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
        
        log_audit("command_received", session_id, {"command": "assist"})
        
        response = await llm_handler.generate_assist(session)
        
        response_generated = time.time()
        telegram_sent = time.time()
        latency_log.append({
            "command": "assist",
            "command_received": cmd_received,
            "response_generated": response_generated,
            "telegram_sent": telegram_sent,
            "total_latency": telegram_sent - cmd_received,
        })
        
        log_audit("response_sent", session_id, {"command": "assist", "latency": telegram_sent - cmd_received})
        
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
        
        log_audit("command_received", session_id, {"command": "say"})
        
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
        
        log_audit("response_sent", session_id, {"command": "say", "latency": telegram_sent - cmd_received})
        
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
        
        log_audit("command_received", session_id, {"command": "followup"})
        
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
        
        log_audit("response_sent", session_id, {"command": "followup", "latency": telegram_sent - cmd_received})
        
        await update.message.reply_text(
            f"❓ *Follow-up Questions*\n\n{response}",
            parse_mode="Markdown"
        )
    
    async def cmd_recap(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recap command."""
        cmd_received = time.time()
        
        active_sessions = session_manager.get_active_sessions()
        
        session = None
        if active_sessions:
            session_id = active_sessions[0]["session_id"]
            session = session_manager.get_session(session_id)
        elif session_manager.sessions:
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
        
        log_audit("command_received", session.session_id, {"command": "recap"})
        
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
        
        log_audit("response_sent", session.session_id, {"command": "recap", "latency": telegram_sent - cmd_received})
        
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
            log_audit("session_stopped", session_id)
        
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
        
        project_info = ""
        if session_info.get("active_project_id"):
            project_info = f"\nActive project: {session_info['active_project_id']}"
        
        await update.message.reply_text(
            f"🎙️ *Session Active*\n\n"
            f"Status: Listening\n"
            f"Duration: {minutes}m {seconds}s\n"
            f"Transcript entries: {session_info['transcript_count']}\n"
            f"Audio chunks: {session_info['metadata']['audio_chunks_received']}"
            f"{project_info}"
        )
    
    # --- Project Commands (MVP) ---
    
    async def cmd_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List available projects."""
        # TODO: Integrate with knowledge base module
        await update.message.reply_text(
            "📁 *Projects*\n\n"
            "No projects configured yet.\n"
            "Use the web API to upload documents and create projects.\n\n"
            "Telegram commands:\n"
            "• /use_project <name> — Set active project\n"
            "• /project_status — Check project status"
        )
    
    async def cmd_use_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set active project for session."""
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /use_project <project_name>\n"
                "Example: /use_project migration-project"
            )
            return
        
        project_name = args[0]
        
        # Set active project for active session
        active_sessions = session_manager.get_active_sessions()
        if active_sessions:
            session_id = active_sessions[0]["session_id"]
            session = session_manager.get_session(session_id)
            session.active_project_id = project_name
            log_audit("project_set", session_id, {"project": project_name})
        
        await update.message.reply_text(
            f"✅ Active project set to: *{project_name}*\n\n"
            f"Commands will now use this project's knowledge base.",
            parse_mode="Markdown"
        )
    
    async def cmd_project_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check project status."""
        active_sessions = session_manager.get_active_sessions()
        
        if not active_sessions:
            await update.message.reply_text("No active session.")
            return
        
        session = session_manager.get_session(active_sessions[0]["session_id"])
        project_id = session.active_project_id
        
        if not project_id:
            await update.message.reply_text(
                "No active project set.\n"
                "Use /use_project <name> to set one."
            )
            return
        
        await update.message.reply_text(
            f"📊 *Project Status*\n\n"
            f"Project: {project_id}\n"
            f"Status: Active\n"
            f"Documents: N/A (MVP)\n"
            f"Indexed: N/A (MVP)"
        )
    
    async def error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        print(f"Telegram error: {context.error}")
        log_audit("telegram_error", details={"error": str(context.error)})
        if update and update.message:
            await update.message.reply_text(
                "⚠️ An error occurred. Please try again."
            )


# Global instance
telegram_bot = TelegramBot()
