"""Unit tests for smart OCR gating."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import app.core.config as config
from app.models.enums import ExtractionState
from app.services.ocr_service import (
    METHOD_DIRECT,
    METHOD_OCR_PRIMARY,
    _is_text_sufficient,
    extract_pdf_resume,
)


def test_is_text_sufficient_by_length():
    assert _is_text_sufficient("x" * 100, page_count=1) is True
    assert _is_text_sufficient("x" * 99, page_count=1) is False


def test_is_text_sufficient_by_chars_per_page():
    text = "a" * 150
    assert _is_text_sufficient(text, page_count=2) is True
    assert _is_text_sufficient(text, page_count=4) is False


def test_extract_pdf_skips_ocr_when_direct_text_sufficient(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    long_text = "Experience: " + ("software engineer " * 20)

    with patch(
        "app.services.ocr_service._direct_extract_pdf",
        return_value=(long_text, 1, "pymupdf"),
    ):
        result = extract_pdf_resume(pdf_path)

    assert result["method"] == METHOD_DIRECT
    assert result["ocr_triggered"] is False
    assert result["state"] == ExtractionState.TEXT_EXTRACTED.value
    assert result["char_count"] == len(long_text.strip())


def test_extract_pdf_runs_ocr_when_direct_text_insufficient(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    ocr_text = "OCR recovered content " * 10

    with patch(
        "app.services.ocr_service._direct_extract_pdf",
        return_value=("short", 2, "pypdf"),
    ), patch(
        "app.services.ocr_service._run_ocr_primary",
        return_value=ocr_text,
    ):
        result = extract_pdf_resume(pdf_path)

    assert result["method"] == METHOD_OCR_PRIMARY
    assert result["ocr_triggered"] is True
    assert result["state"] == ExtractionState.OCR_DONE.value
    assert result["char_count"] >= config.TEXT_MIN_LENGTH


def test_extract_pdf_ocr_failed_does_not_raise(tmp_path):
    pdf_path = tmp_path / "bad.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch(
        "app.services.ocr_service._direct_extract_pdf",
        return_value=("", 1, "pypdf"),
    ), patch(
        "app.services.ocr_service._run_ocr_primary",
        side_effect=TimeoutError("tesseract timed out"),
    ), patch(
        "app.services.ocr_service._run_ocr_fallback",
        side_effect=ValueError("easyocr not installed"),
    ):
        result = extract_pdf_resume(pdf_path)

    assert result["state"] == ExtractionState.OCR_FAILED.value
    assert result["ocr_triggered"] is True
    assert "failure_reason" in result
