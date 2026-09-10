import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Detect active environment file (defaults to config/local.env)
ENV_MODE = os.getenv("ENV_MODE", "local").lower()
ENV_FILE_PATH = BASE_DIR / "config" / f"{ENV_MODE}.env"
if not ENV_FILE_PATH.exists():
    ENV_FILE_PATH = BASE_DIR / "config" / "local.env"


class Settings(BaseSettings):
    """
    Central Application Settings loaded from config/{ENV_MODE}.env
    """
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application Settings
    APP_NAME: str = "AI Interview Copilot"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # LLM Routing Flag
    # False = Free Cloud API (Default: Google Gemini)
    # True  = Local Open-Source LLM (Ollama / Local Server)
    USE_OPEN_SOURCE: bool = False

    # Cloud LLM Settings (Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Local Open-Source LLM Settings
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3.2"

    # ==========================================
    # V2: Vector Embeddings & RAG Configuration
    # ==========================================
    # Flag: LOCAL_EMBED / USE_LOCAL_EMBEDDINGS
    # False = Cloud API (Google Gemini text-embedding-004)
    # True  = Local Embeddings (Ollama / SentenceTransformers / In-Memory Fallback)
    USE_LOCAL_EMBEDDINGS: bool = False
    LOCAL_EMBED: bool = False  # Friendly alias

    # Cloud Embedding Model
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Local Embedding Settings
    LOCAL_EMBEDDING_BASE_URL: str = "http://localhost:11434"
    LOCAL_EMBEDDING_MODEL: str = "nomic-embed-text"

    # Vector Database Storage Path
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")

    @property
    def is_local_embed(self) -> bool:
        """Returns True if either LOCAL_EMBED or USE_LOCAL_EMBEDDINGS is enabled."""
        return self.LOCAL_EMBED or self.USE_LOCAL_EMBEDDINGS


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid reloading environment files repeatedly."""
    return Settings()


settings = get_settings()
