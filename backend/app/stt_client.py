import asyncio
import json
import time
from typing import Optional

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)

from app.config import get_settings
from app.session_manager import session_manager
from app.security import log_audit

settings = get_settings()


class DeepgramSTT:
    """Streaming STT handler using Deepgram."""
    
    def __init__(self):
        self.client = DeepgramClient(settings.deepgram_api_key)
        self.connections: dict[str, any] = {}
    
    async def start_stream(self, session_id: str) -> Optional[any]:
        """Start a new Deepgram streaming connection."""
        try:
            dg_connection = self.client.listen.websocket.v("1")
            
            # Event handlers
            def on_open(self, open, **kwargs):
                print(f"Deepgram connection opened for session {session_id}")
            
            def on_message(self, result, **kwargs):
                transcript = result.channel.alternatives[0].transcript
                if transcript.strip():
                    is_final = result.is_final
                    session = session_manager.get_session(session_id)
                    if session:
                        session.add_transcript(transcript, is_final=is_final)
                        print(f"[{'FINAL' if is_final else 'INTERIM'}] {transcript}")
            
            def on_close(self, close, **kwargs):
                print(f"Deepgram connection closed for session {session_id}")
            
            def on_error(self, error, **kwargs):
                print(f"Deepgram error for session {session_id}: {error}")
            
            dg_connection.on(LiveTranscriptionEvents.Open, on_open)
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            
            # Configure options
            options = LiveOptions(
                model="nova-2",
                language="en",
                smart_format=True,
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                interim_results=True,
                punctuate=True,
                endpointing=500,
            )
            
            # Start connection
            await dg_connection.start(options)
            self.connections[session_id] = dg_connection
            
            return dg_connection
            
        except Exception as e:
            print(f"Failed to start Deepgram stream: {e}")
            return None
    
    async def send_audio(self, session_id: str, audio_chunk: bytes):
        """Send audio chunk to Deepgram."""
        connection = self.connections.get(session_id)
        if connection:
            await connection.send(audio_chunk)
            
            session = session_manager.get_session(session_id)
            if session:
                session.metadata["audio_chunks_received"] += 1
    
    async def stop_stream(self, session_id: str):
        """Stop Deepgram streaming connection."""
        connection = self.connections.pop(session_id, None)
        if connection:
            await connection.finish()
            print(f"Deepgram stream stopped for session {session_id}")


# Global instance
deepgram_stt = DeepgramSTT()
