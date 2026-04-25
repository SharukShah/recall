"""
Configuration management using pydantic-settings.
Loads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Database
    DATABASE_URL: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Search defaults
    SEARCH_DEFAULT_LIMIT: int = 5
    SEARCH_MIN_SIMILARITY: float = 0.3
    SEARCH_MAX_CONTEXT_TOKENS: int = 3000

    # Deepgram Voice Agent
    DEEPGRAM_API_KEY: str = ""
    DEEPGRAM_ENABLED: bool = False
    MAX_VOICE_SESSION_MINUTES: int = 15
    MAX_VOICE_MINUTES_PER_DAY: int = 60
    DEEPGRAM_VOICE_MODEL: str = "aura-2-andromeda-en"
    DEEPGRAM_STT_MODEL: str = "nova-3"
    DEEPGRAM_LLM_MODEL: str = "gpt-4.1-nano"

    # Push Notifications (VAPID)
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@recall.local"

    # Authentication (single-user MVP)
    API_KEY: str = ""  # If empty, auth is disabled (development mode)

    # App
    ENV: str = "development"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Global settings instance
settings = Settings()
