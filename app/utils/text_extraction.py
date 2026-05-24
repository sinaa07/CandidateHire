from pathlib import Path
import logging
from typing import Optional
from docx import Document

from app.services.ocr_service import extract_pdf_resume
from app.utils.latency_tracker import LatencyRecorder, STAGE_TEXT_EXTRACTION

logger = logging.getLogger(__name__)


def extract_text(
    file_path: Path,
    use_ocr_fallback: bool = True,
    recorder: Optional[LatencyRecorder] = None,
) -> str:
    """
    Extract plain text from resume files.

    PDFs use smart OCR gating via ``ocr_service`` when ``use_ocr_fallback`` is True.
    DOCX and TXT use direct extraction only.

    Args:
        file_path: Path to the file.
        use_ocr_fallback: For PDFs, enable smart OCR gating (default True).
        recorder: Optional latency recorder.

    Returns:
        Extracted text (empty string if none found).

    Raises:
        Exception: If the file is unreadable or unsupported.
    """
    try:
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            if use_ocr_fallback:
                result = extract_pdf_resume(file_path, recorder=recorder)
                return result.get("text", "")
            return _extract_pdf_direct_only(file_path, recorder=recorder)
        if suffix == ".docx":
            return _extract_docx(file_path, recorder=recorder)
        if suffix == ".txt":
            return _extract_txt(file_path, recorder=recorder)
        raise ValueError(f"Unsupported file type: {suffix}")
    except Exception as exc:
        raise Exception(f"Failed to extract text from {file_path.name}") from exc


def _extract_pdf_direct_only(
    file_path: Path,
    recorder: Optional[LatencyRecorder] = None,
) -> str:
    """Extract PDF text without OCR (direct engines only)."""
    from app.services.ocr_service import _direct_extract_pdf

    if recorder:
        with recorder.stage(STAGE_TEXT_EXTRACTION):
            text, _, _ = _direct_extract_pdf(file_path)
    else:
        text, _, _ = _direct_extract_pdf(file_path)
    return text


def _extract_docx(file_path: Path, recorder: Optional[LatencyRecorder] = None) -> str:
    try:
        if recorder:
            with recorder.stage(STAGE_TEXT_EXTRACTION):
                result = _docx_text_extract(file_path)
        else:
            result = _docx_text_extract(file_path)
        if not result:
            raise ValueError("DOCX file appears to be empty or contains no extractable text")
        return result
    except Exception as exc:
        if "empty" in str(exc).lower() or "no extractable text" in str(exc).lower():
            raise
        raise Exception(f"DOCX extraction error: {exc}") from exc


def _docx_text_extract(file_path: Path) -> str:
    doc = Document(file_path)
    text = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
    return " ".join(text).strip()


def _extract_txt(file_path: Path, recorder: Optional[LatencyRecorder] = None) -> str:
    if recorder:
        with recorder.stage(STAGE_TEXT_EXTRACTION):
            return _txt_read(file_path)
    return _txt_read(file_path)


def _txt_read(file_path: Path) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read().strip()
