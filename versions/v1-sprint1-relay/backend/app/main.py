import asyncio
import time
import uuid
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.session_manager import session_manager
from app.security import log_audit
from app.telegram_commands import telegram_bot
from app.project_routes import router as project_router

settings = get_settings()
app = FastAPI(title="Meeting Assistant API")

# Include project routes
app.include_router(project_router)

# Serve APK file
@app.get("/download/apk")
async def download_apk():
    """Download the latest debug APK."""
    apk_path = "/root/.openclaw/workspace/meeting-assistant/android/app/build/outputs/apk/debug/app-debug.apk"
    return FileResponse(apk_path, filename="meeting-assistant.apk", media_type="application/vnd.android.package-archive")


@app.on_event("startup")
async def startup_event():
    """Start Telegram bot on server startup."""
    # Telegram bot enabled
    await telegram_bot.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Telegram bot enabled
    await telegram_bot.stop()


# --- LLM Test Endpoints ---

@app.post("/test/say")
async def test_say(data: dict):
    """Test /say command with project context."""
    session_id = data.get("session_id", "test-session-001")
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from app.answer_generator import llm_handler
    response = await llm_handler.generate_say(session)
    
    return {
        "session_id": session_id,
        "project_id": session.active_project_id,
        "latest_question": session.get_latest_question(),
        "response": response,
    }


@app.post("/test/assist")
async def test_assist(data: dict):
    """Test /assist command with project context."""
    session_id = data.get("session_id", "test-session-001")
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from app.answer_generator import llm_handler
    response = await llm_handler.generate_assist(session)
    
    return {
        "session_id": session_id,
        "project_id": session.active_project_id,
        "response": response,
    }


@app.post("/test/recap")
async def test_recap(data: dict):
    """Test /recap command."""
    session_id = data.get("session_id", "test-session-001")
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from app.answer_generator import llm_handler
    response = await llm_handler.generate_recap(session)
    
    return {
        "session_id": session_id,
        "project_id": session.active_project_id,
        "response": response,
    }


# --- Test/Simulation Endpoints ---

@app.post("/session/simulate")
async def simulate_session(data: dict):
    """Simulate a meeting session with transcript for testing."""
    session_id = data.get("session_id", "simulated-session")
    transcript_lines = data.get("transcript", [])
    project_id = data.get("project_id")
    
    # Create session
    session = session_manager.get_or_create(session_id)
    session.is_active = True
    
    # Add transcript lines
    for line in transcript_lines:
        session.add_transcript(line, is_final=True)
    
    # Set project if provided
    if project_id:
        session.active_project_id = project_id
    
    log_audit("session_simulated", session_id, {
        "transcript_lines": len(transcript_lines),
        "project_id": project_id,
    })
    
    return {
        "session_id": session_id,
        "status": "active",
        "transcript_count": len(session.transcript),
        "project_id": session.active_project_id,
    }


@app.post("/session/clear")
async def clear_session(data: dict):
    """Clear a simulated session."""
    session_id = data.get("session_id")
    if session_id and session_id in session_manager.sessions:
        del session_manager.sessions[session_id]
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}


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
        log_audit("session_started", session_id)
        
        # Create or get session
        session = session_manager.get_or_create(session_id)
        session.metadata["websocket_connected"] = start_time
        
        # Start Deepgram stream
        from app.stt_client import deepgram_stt
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
        
        # Telegram notification disabled
        # await telegram_bot.send_message(
        #     f"🎙️ *Meeting Started*\nSession: `{session_id[:8]}`"
        # )
        
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
            from app.stt_client import deepgram_stt
            await deepgram_stt.stop_stream(session_id)
            session = session_manager.get_session(session_id)
            if session:
                session.metadata["websocket_disconnected"] = time.time()
                duration = time.time() - start_time
                session.metadata["total_duration"] = duration
                # Auto-save transcript before ending session
                try:
                    session.save_transcript()
                except Exception as e:
                    print(f"Failed to save transcript: {e}")
                log_audit("session_ended", session_id, {"duration": duration})
        
        await websocket.close()
        print(f"Audio stream ended: session={session_id}")


# --- Latency Metrics ---

@app.get("/metrics/latency")
async def get_latency_metrics():
    """Get latency metrics for commands."""
    from app.telegram_commands import latency_log
    
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
