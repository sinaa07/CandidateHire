"""
Backward-compatible OCR helpers.

New code should use ``app.services.ocr_service`` directly.
"""
from __future__ import annotations

from pathlib import Path

from app.services.ocr_service import extract_pdf_resume


def is_ocr_available() -> bool:
    """Return True when tesseract OCR dependencies are importable."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_text_with_ocr(pdf_path: Path, dpi: int = 150, lang: str = "eng") -> str:
    """
    Extract text from a PDF using the smart OCR pipeline.

    Deprecated: prefer ``extract_pdf_resume`` from ``ocr_service``.
    """
    result = extract_pdf_resume(pdf_path)
    text = result.get("text", "")
    if not text and result.get("state") == "OCR_FAILED":
        reason = result.get("failure_reason", "OCR failed")
        raise ValueError(reason)
    return text


def should_use_ocr(extracted_text: str, min_char_threshold: int) -> bool:
    """Return True when stripped text length is below the threshold."""
    if not extracted_text:
        return True
    return len(extracted_text.strip()) < min_char_threshold
