from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Deepgram
    deepgram_api_key: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # Fast & cheap for MVP
    
    # Kimi (optional fallback)
    kimi_api_key: str = ""
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = "134036214"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    backend_auth_token: str = ""
    
    # Session
    max_buffer_minutes: int = 60
    transcript_max_lines: int = 500
    
    # Storage toggles
    transcript_storage_enabled: bool = False
    raw_audio_storage_enabled: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
