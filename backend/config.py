from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Deepgram
    deepgram_api_key: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # Fast & cheap for MVP
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = "134036214"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Session
    max_buffer_minutes: int = 60
    transcript_max_lines: int = 500
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
