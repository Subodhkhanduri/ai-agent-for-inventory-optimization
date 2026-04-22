"""
Configuration settings for the Inventory Chatbot application.
Uses pydantic-settings to load values from .env automatically.
"""

import logging
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Force .env to load first (overrides OS environment variables)
# ------------------------------------------------------------------
env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(env_path, override=True)

# ------------------------------------------------------------------
# Fix Windows WinError 2 (wmic not found) for joblib/loky
# ------------------------------------------------------------------
if os.name == 'nt' and "LOKY_MAX_CPU_COUNT" not in os.environ:
    os.environ["LOKY_MAX_CPU_COUNT"] = str(os.cpu_count())


class Settings(BaseSettings):
    """Application configuration — values are loaded from .env automatically."""

    # --- API Configuration ---
    API_TITLE: str = "Inventory Management Chatbot API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # --- Groq LLM Configuration ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # --- Security ---
    JWT_SECRET_KEY: str = "change-this-to-a-strong-random-secret-in-production"

    # --- Database Configuration ---
    DATABASE_URL: str = "sqlite:///./inventory.db"

    # --- Redis Configuration ---
    REDIS_URL: str = "redis://localhost:6379"

    # --- File Upload Configuration ---
    MAX_FILE_SIZE_MB: int = 200
    ALLOWED_FILE_TYPES: list = ["csv"]

    # --- Server Configuration ---
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    RELOAD: bool = True

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


# Instantiate settings after .env is loaded
settings = Settings()


def validate_settings():
    """Validate critical settings at startup."""
    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is missing! Add GROQ_API_KEY=your_key to .env"
        )

    if settings.JWT_SECRET_KEY == "change-this-to-a-strong-random-secret-in-production":
        logger.warning("JWT_SECRET_KEY is using the default value — set a strong secret in .env for production")

    logger.info("Settings validated successfully")
    logger.info(f"  GROQ Model: {settings.GROQ_MODEL}")
    logger.info(f"  API Prefix: {settings.API_PREFIX}")
