import asyncio
import time
import uuid
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from config import get_settings
from session_manager import session_manager
from stt_provider import deepgram_stt
from telegram_bot import telegram_bot

settings = get_settings()
app = FastAPI(title="Meeting Assistant API")


@app.on_event("startup")
async def startup_event():
    """Start Telegram bot on server startup."""
    await telegram_bot.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await telegram_bot.stop()


# --- Health & Test Endpoints ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "active_sessions": len(session_manager.get_active_sessions()),
    }


@app.post("/telegram/test")
async def test_telegram():
    """Send test message to Telegram."""
    try:
        await telegram_bot.send_message(
            "🧪 *Test Message*\nMeeting assistant backend is running!"
        )
        return {"status": "sent", "message": "Test message sent to Telegram"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Session Endpoints ---

@app.get("/session/status")
async def session_status():
    """Get active session status."""
    active = session_manager.get_active_sessions()
    return {
        "active_sessions": active,
        "total_sessions": len(session_manager.sessions),
    }


# --- WebSocket Audio Stream ---

@app.websocket("/audio-stream")
async def audio_stream(websocket: WebSocket):
    """WebSocket endpoint for audio streaming from Android."""
    await websocket.accept()
    
    session_id = None
    start_time = time.time()
    
    try:
        # Wait for initial metadata (session_id, etc.)
        data = await websocket.receive_json()
        session_id = data.get("session_id", str(uuid.uuid4()))
        
        print(f"Audio stream started: session={session_id}")
        
        # Create or get session
        session = session_manager.get_or_create(session_id)
        session.metadata["websocket_connected"] = start_time
        
        # Start Deepgram stream
        dg_connection = await deepgram_stt.start_stream(session_id)
        if not dg_connection:
            await websocket.send_json({
                "status": "error",
                "message": "Failed to start STT stream"
            })
            return
        
        await websocket.send_json({
            "status": "connected",
            "session_id": session_id,
        })
        
        # Send Telegram notification
        await telegram_bot.send_message(
            f"🎙️ *Meeting Started*\nSession: `{session_id[:8]}`"
        )
        
        # Receive audio chunks
        while True:
            try:
                # Receive binary audio data
                message = await websocket.receive()
                
                if "bytes" in message:
                    audio_chunk = message["bytes"]
                    
                    # Send to Deepgram
                    await deepgram_stt.send_audio(session_id, audio_chunk)
                    
                elif "text" in message:
                    # Handle control messages
                    data = message["text"]
                    if data == "ping":
                        await websocket.send_text("pong")
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        print(f"Audio stream error: {e}")
        
    finally:
        # Cleanup
        if session_id:
            await deepgram_stt.stop_stream(session_id)
            session = session_manager.get_session(session_id)
            if session:
                session.metadata["websocket_disconnected"] = time.time()
                duration = time.time() - start_time
                session.metadata["total_duration"] = duration
        
        await websocket.close()
        print(f"Audio stream ended: session={session_id}")


# --- Latency Metrics ---

@app.get("/metrics/latency")
async def get_latency_metrics():
    """Get latency metrics for commands."""
    from telegram_bot import latency_log
    
    if not latency_log:
        return {"metrics": [], "average_latency": 0}
    
    avg_latency = sum(m["total_latency"] for m in latency_log) / len(latency_log)
    
    return {
        "metrics": latency_log[-20:],  # Last 20 entries
        "average_latency": round(avg_latency, 2),
        "total_commands": len(latency_log),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
