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
    APP_VERSION: str = "1.0.0"
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
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Local Open-Source LLM Settings (Future Open-Source Routing)
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3.2"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid reloading environment files repeatedly."""
    return Settings()


settings = get_settings()
