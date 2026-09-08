from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Deepgram
    deepgram_api_key: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    kimi_api_key: str = ""
    kimi_model: str = "kimi/kimi-for-coding"
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = "134036214"
    
    # Security
    backend_auth_token: str = ""  # For Android auth
    
    # Storage flags
    transcript_storage_enabled: bool = False
    raw_audio_storage_enabled: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Session
    max_buffer_minutes: int = 60
    transcript_max_lines: int = 500
    
    # Knowledge Base
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
