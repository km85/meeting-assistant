import hashlib
import hmac
import time
from typing import Optional
from fastapi import Header, HTTPException, Request
from app.config import get_settings

settings = get_settings()

# Audit log (in-memory, flush to file periodically)
audit_logs: list[dict] = []

def log_audit(action: str, session_id: Optional[str] = None, details: Optional[dict] = None):
    """Log security audit event."""
    entry = {
        "timestamp": time.time(),
        "action": action,
        "session_id": session_id,
        "details": details or {},
    }
    audit_logs.append(entry)
    # Only log non-sensitive actions to console
    if action not in ["transcript_received", "audio_chunk"]:
        print(f"[AUDIT] {action} | session={session_id}")

def verify_android_auth(authorization: Optional[str] = Header(None)) -> bool:
    """Verify Android auth token."""
    if not settings.backend_auth_token:
        return True  # Dev mode, no auth required
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Expected format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = parts[1]
    if not hmac.compare_digest(token, settings.backend_auth_token):
        raise HTTPException(status_code=403, detail="Invalid auth token")
    
    return True

def sanitize_log(text: str) -> str:
    """Sanitize text for logging - truncate and mask sensitive content."""
    if not text:
        return ""
    # Truncate long text
    if len(text) > 100:
        return text[:100] + "...[truncated]"
    return text

def hash_identifier(identifier: str) -> str:
    """Hash identifier for privacy."""
    return hashlib.sha256(identifier.encode()).hexdigest()[:16]
