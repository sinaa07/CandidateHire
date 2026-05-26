"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CandidateHire"
    APP_ENV: str = "development"  # development | production
    DEBUG: bool = True

    # JWT
    JWT_SECRET_KEY: str  # REQUIRED — must be set in .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./storage/candidatehire.db"

    # LLM
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Security
    BCRYPT_ROUNDS: int = 12

    # Registration
    REGISTRATION_OPEN: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Legacy module-level paths and OCR flags (used by v1 pipeline code)
BASE_STORAGE_PATH = Path("storage")
COLLECTIONS_ROOT = BASE_STORAGE_PATH / "companies"

OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() in ("1", "true", "yes")
OCR_MIN_CHAR_THRESHOLD = int(os.getenv("OCR_MIN_CHAR_THRESHOLD", "100"))

TEXT_MIN_LENGTH = int(os.getenv("TEXT_MIN_LENGTH", "100"))
TEXT_MIN_CHARS_PER_PAGE = int(os.getenv("TEXT_MIN_CHARS_PER_PAGE", "50"))
OCR_PRIMARY = os.getenv("OCR_PRIMARY", "tesseract").lower()
OCR_TIMEOUT_SECONDS = int(os.getenv("OCR_TIMEOUT_SECONDS", "30"))
OCR_MAX_RETRIES = int(os.getenv("OCR_MAX_RETRIES", "2"))
