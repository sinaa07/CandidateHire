from pathlib import Path

BASE_STORAGE_PATH = Path("storage")
COLLECTIONS_ROOT = BASE_STORAGE_PATH / "companies"

# OCR Configuration
OCR_MIN_CHAR_THRESHOLD = 100  # Minimum characters to avoid OCR (text-based PDFs)
OCR_ENABLED = True  # Set to False to disable OCR fallback