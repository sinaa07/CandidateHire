"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_STORAGE_PATH = Path("storage")
COLLECTIONS_ROOT = BASE_STORAGE_PATH / "companies"

# Legacy OCR flags (kept for backward compatibility)
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() in ("1", "true", "yes")
OCR_MIN_CHAR_THRESHOLD = int(os.getenv("OCR_MIN_CHAR_THRESHOLD", "100"))

# Smart OCR gating
TEXT_MIN_LENGTH = int(os.getenv("TEXT_MIN_LENGTH", "100"))
TEXT_MIN_CHARS_PER_PAGE = int(os.getenv("TEXT_MIN_CHARS_PER_PAGE", "50"))
OCR_PRIMARY = os.getenv("OCR_PRIMARY", "tesseract").lower()
OCR_TIMEOUT_SECONDS = int(os.getenv("OCR_TIMEOUT_SECONDS", "30"))
OCR_MAX_RETRIES = int(os.getenv("OCR_MAX_RETRIES", "2"))
