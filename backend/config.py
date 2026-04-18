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

    # App
    ENV: str = "development"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Global settings instance
settings = Settings()
