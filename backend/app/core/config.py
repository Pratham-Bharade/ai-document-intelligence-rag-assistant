"""
File: backend/app/core/config.py
Purpose: Centralized application configuration
Why it exists: Configuration must be centralized so that:
               1. Settings are validated on startup (fail fast, not mid-request)
               2. Environment variables are typed (not just raw strings)
               3. Any part of the app imports from ONE place, not scattered os.getenv()
Dependencies: pydantic-settings, python-dotenv
Main responsibilities:
  - Load environment variables from .env
  - Validate types and required fields
  - Provide typed access to all configuration
  - Export a singleton `settings` object used throughout the app
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic BaseSettings automatically:
    1. Reads values from environment variables
    2. Reads values from .env file (if dotenv_path is specified)
    3. Validates types (DATABASE_URL must be a string, PORT must be int, etc.)
    4. Raises clear errors on startup if required values are missing
    
    This is much better than scattered os.getenv() calls because:
    - All configuration is in one place
    - Types are validated immediately
    - Missing required config fails fast at startup
    - Easy to see ALL config options in one file
    """

    model_config = SettingsConfigDict(
        env_file=".env",            # Read from .env file in project root
        env_file_encoding="utf-8",
        case_sensitive=False,        # DATABASE_URL and database_url both work
        extra="ignore",              # Ignore unknown env vars (don't crash)
    )

    # =========================================================================
    # APPLICATION
    # =========================================================================
    environment: Literal["development", "production", "testing"] = "development"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # =========================================================================
    # DATABASE
    # =========================================================================
    # We use a default that works for local PostgreSQL.
    # In production, this MUST be overridden in .env
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/rag_assistant"

    # =========================================================================
    # JWT AUTHENTICATION
    # =========================================================================
    jwt_secret: str = "CHANGE_THIS_IN_PRODUCTION_USE_ENV_FILE"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # =========================================================================
    # LLM CONFIGURATION
    # =========================================================================
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model_name: str = "llama-3.3-70b-versatile"
    llm_base_url: str = "https://api.groq.com/openai/v1"

    # =========================================================================
    # EMBEDDING CONFIGURATION
    # =========================================================================
    embedding_provider: Literal["local", "openai"] = "local"
    # Local model: fast, free, runs on CPU, 384 dimensions
    embedding_model_name: str = "all-MiniLM-L6-v2"
    # OpenAI embedding model (only used when embedding_provider="openai")
    openai_embedding_model: str = "text-embedding-3-small"

    # =========================================================================
    # FILE UPLOAD
    # =========================================================================
    max_file_size_mb: int = 50
    upload_dir: str = "uploads"

    # =========================================================================
    # RAG CONFIGURATION
    # =========================================================================
    retrieval_top_k: int = 5           # How many chunks to retrieve per query
    chunk_size: int = 1000             # Characters per chunk (approx)
    chunk_overlap: int = 200           # Character overlap between chunks

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes for comparison with actual file sizes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


# =============================================================================
# SINGLETON PATTERN WITH LRU CACHE
# =============================================================================
# We use @lru_cache to ensure only ONE Settings object is ever created.
# Without this, every import would create a new Settings, re-reading .env.
# With lru_cache, the first call creates it; all subsequent calls return the same object.
#
# Usage anywhere in the app:
#   from app.core.config import get_settings
#   settings = get_settings()
#   print(settings.database_url)

@lru_cache()
def get_settings() -> Settings:
    """
    Return the application settings singleton.
    
    Uses lru_cache so the .env file is only read once.
    In tests, you can override this with app.dependency_overrides.
    """
    return Settings()


# Convenience export — most code can just do: from app.core.config import settings
settings = get_settings()
