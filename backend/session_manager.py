import asyncio
import time
from collections import deque
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class TranscriptEntry:
    text: str
    timestamp: float = field(default_factory=time.time)
    is_final: bool = True
    speaker: Optional[str] = None


class Session:
    def __init__(self, session_id: str, max_lines: int = 500):
        self.session_id = session_id
        self.created_at = time.time()
        self.transcript: deque[TranscriptEntry] = deque(maxlen=max_lines)
        self.is_active = True
        self.last_activity = time.time()
        self.metadata = {
            "audio_chunks_received": 0,
            "transcript_entries": 0,
        }
    
    def add_transcript(self, text: str, is_final: bool = True):
        entry = TranscriptEntry(text=text, is_final=is_final)
        self.transcript.append(entry)
        self.last_activity = time.time()
        if is_final:
            self.metadata["transcript_entries"] += 1
    
    def get_recent_transcript(self, minutes: int = 10) -> str:
        cutoff = time.time() - (minutes * 60)
        recent = [e for e in self.transcript if e.timestamp > cutoff]
        return "\n".join([e.text for e in recent])
    
    def get_full_transcript(self) -> str:
        return "\n".join([e.text for e in self.transcript])
    
    def get_latest_question(self) -> Optional[str]:
        """Find latest question from transcript using simple heuristics."""
        question_indicators = [
            "?", "who", "what", "when", "where", "why", "how",
            "can we", "should we", "do we", "are we", "is it", "could we",
            "i'm not sure why", "i don't understand", "this seems too",
            "i'm concerned about", "it is unclear", "wondering if",
            "question", "ask", "confirm", "clarify"
        ]
        
        # Search from newest to oldest
        for entry in reversed(self.transcript):
            text_lower = entry.text.lower()
            if any(ind in text_lower for ind in question_indicators):
                return entry.text
        
        return None
    
    def stop(self):
        self.is_active = False
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "transcript_count": len(self.transcript),
            "metadata": self.metadata,
        }


class SessionManager:
    def __init__(self, max_lines: int = 500):
        self.sessions: dict[str, Session] = {}
        self.max_lines = max_lines
    
    def create_session(self, session_id: str) -> Session:
        session = Session(session_id, max_lines=self.max_lines)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)
    
    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self.sessions:
            return self.create_session(session_id)
        return self.sessions[session_id]
    
    def end_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id].stop()
            # Keep transcript briefly for /recap after stop, then clean up
            return True
        return False
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        cutoff = time.time() - (max_age_hours * 3600)
        to_remove = [
            sid for sid, s in self.sessions.items()
            if not s.is_active and s.last_activity < cutoff
        ]
        for sid in to_remove:
            del self.sessions[sid]
    
    def get_active_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self.sessions.values() if s.is_active]


# Global instance
session_manager = SessionManager()
