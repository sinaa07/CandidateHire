"""
Smart OCR gating for PDF resume ingestion.

Attempts direct text extraction first; runs OCR only when extracted text is
insufficient. OCR stack: pytesseract (primary) → easyocr (fallback) → OCR_FAILED.
"""
from __future__ import annotations

import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any, Callable, Optional

import app.core.config as config
from app.models.enums import ExtractionState
from app.utils.latency_tracker import LatencyRecorder, STAGE_OCR, STAGE_TEXT_EXTRACTION

logger = logging.getLogger(__name__)

METHOD_DIRECT = "direct"
METHOD_OCR_PRIMARY = "ocr_primary"
METHOD_OCR_FALLBACK = "ocr_fallback"

TypeExtractionResult = dict[str, Any]


def extract_pdf_resume(
    pdf_path: Path,
    recorder: Optional[LatencyRecorder] = None,
) -> TypeExtractionResult:
    """
    Extract text from a PDF with smart OCR gating.

    Returns a dict with keys: text, method, char_count, ocr_triggered, state,
    latency_ms, and optionally failure_reason.
    """
    start = time.perf_counter()
    page_count = 0
    direct_text = ""
    direct_backend = "none"

    try:
        if recorder:
            with recorder.stage(STAGE_TEXT_EXTRACTION):
                direct_text, page_count, direct_backend = _direct_extract_pdf(pdf_path)
        else:
            direct_text, page_count, direct_backend = _direct_extract_pdf(pdf_path)
    except Exception as exc:
        logger.warning(
            "Direct PDF extraction failed for %s (%s): %s",
            pdf_path.name,
            direct_backend,
            exc,
        )
        direct_text = ""
        page_count = _pdf_page_count_safe(pdf_path)

    stripped = direct_text.strip()
    char_count = len(stripped)

    if _is_text_sufficient(stripped, page_count):
        latency_ms = (time.perf_counter() - start) * 1000
        result = _build_result(
            text=stripped,
            method=METHOD_DIRECT,
            char_count=char_count,
            ocr_triggered=False,
            state=ExtractionState.TEXT_EXTRACTED,
            latency_ms=latency_ms,
        )
        _log_extraction(pdf_path.name, result, direct_backend=direct_backend)
        return result

    if not config.OCR_ENABLED:
        latency_ms = (time.perf_counter() - start) * 1000
        reason = "OCR disabled; direct text insufficient"
        result = _build_result(
            text=stripped,
            method=METHOD_DIRECT,
            char_count=char_count,
            ocr_triggered=False,
            state=ExtractionState.OCR_FAILED,
            latency_ms=latency_ms,
            failure_reason=reason,
        )
        _log_extraction(pdf_path.name, result, direct_backend=direct_backend)
        return result

    logger.info(
        "OCR triggered for %s: %d chars, %d pages (min_len=%d, min_chars_per_page=%d)",
        pdf_path.name,
        char_count,
        page_count,
        config.TEXT_MIN_LENGTH,
        config.TEXT_MIN_CHARS_PER_PAGE,
    )
    _log_state(pdf_path.name, ExtractionState.OCR_PENDING)

    ocr_start = time.perf_counter()
    primary_text: Optional[str] = None
    primary_error: Optional[str] = None

    for attempt in range(1, config.OCR_MAX_RETRIES + 1):
        try:
            if recorder:
                with recorder.stage(STAGE_OCR):
                    primary_text = _run_ocr_primary(pdf_path)
            else:
                primary_text = _run_ocr_primary(pdf_path)
            if primary_text and primary_text.strip():
                break
            primary_error = "primary OCR returned no text"
        except Exception as exc:
            primary_error = str(exc)
            logger.warning(
                "Primary OCR attempt %d/%d failed for %s: %s",
                attempt,
                config.OCR_MAX_RETRIES,
                pdf_path.name,
                exc,
            )

    if primary_text and primary_text.strip():
        text = primary_text.strip()
        latency_ms = (time.perf_counter() - start) * 1000
        result = _build_result(
            text=text,
            method=METHOD_OCR_PRIMARY,
            char_count=len(text),
            ocr_triggered=True,
            state=ExtractionState.OCR_DONE,
            latency_ms=latency_ms,
        )
        _log_extraction(
            pdf_path.name,
            result,
            ocr_ms=(time.perf_counter() - ocr_start) * 1000,
        )
        return result

    fallback_text: Optional[str] = None
    fallback_error: Optional[str] = None
    try:
        if recorder:
            with recorder.stage(STAGE_OCR):
                fallback_text = _run_ocr_fallback(pdf_path)
        else:
            fallback_text = _run_ocr_fallback(pdf_path)
    except Exception:
        fallback_error = traceback.format_exc()
        logger.error(
            "Fallback OCR failed for %s:\n%s",
            pdf_path.name,
            fallback_error,
        )

    if fallback_text and fallback_text.strip():
        text = fallback_text.strip()
        latency_ms = (time.perf_counter() - start) * 1000
        result = _build_result(
            text=text,
            method=METHOD_OCR_FALLBACK,
            char_count=len(text),
            ocr_triggered=True,
            state=ExtractionState.OCR_DONE,
            latency_ms=latency_ms,
        )
        _log_extraction(
            pdf_path.name,
            result,
            ocr_ms=(time.perf_counter() - ocr_start) * 1000,
        )
        return result

    failure_parts = []
    if primary_error:
        failure_parts.append(f"primary: {primary_error}")
    if fallback_error:
        failure_parts.append(f"fallback: {fallback_error}")
    if not failure_parts:
        failure_parts.append("both OCR methods returned no text")

    failure_reason = "; ".join(failure_parts)
    latency_ms = (time.perf_counter() - start) * 1000
    best_text = stripped
    if primary_text and len(primary_text.strip()) > len(best_text):
        best_text = primary_text.strip()
    if fallback_text and len(fallback_text.strip()) > len(best_text):
        best_text = fallback_text.strip()

    result = _build_result(
        text=best_text,
        method=METHOD_OCR_PRIMARY if primary_text else METHOD_OCR_FALLBACK,
        char_count=len(best_text),
        ocr_triggered=True,
        state=ExtractionState.OCR_FAILED,
        latency_ms=latency_ms,
        failure_reason=failure_reason,
    )
    _log_extraction(pdf_path.name, result, ocr_ms=(time.perf_counter() - ocr_start) * 1000)
    return result


def _is_text_sufficient(text: str, page_count: int) -> bool:
    """Return True when direct extraction has enough text to skip OCR."""
    stripped_len = len(text.strip())
    if stripped_len < config.TEXT_MIN_LENGTH:
        return False
    if page_count <= 0:
        return stripped_len >= config.TEXT_MIN_LENGTH
    chars_per_page = stripped_len / page_count
    return chars_per_page >= config.TEXT_MIN_CHARS_PER_PAGE


def _direct_extract_pdf(pdf_path: Path) -> tuple[str, int, str]:
    """
    Extract text via PyMuPDF, pdfplumber, or pypdf (first available).

    Returns:
        Tuple of (full_text, page_count, backend_name).
    """
    errors: list[str] = []

    try:
        import fitz  # PyMuPDF

        return _extract_with_fitz(pdf_path)
    except ImportError:
        errors.append("pymupdf not installed")
    except Exception as exc:
        errors.append(f"pymupdf: {exc}")

    try:
        import pdfplumber

        return _extract_with_pdfplumber(pdf_path)
    except ImportError:
        errors.append("pdfplumber not installed")
    except Exception as exc:
        errors.append(f"pdfplumber: {exc}")

    try:
        return _extract_with_pypdf(pdf_path)
    except Exception as exc:
        errors.append(f"pypdf: {exc}")
        raise RuntimeError(
            f"All direct PDF extractors failed for {pdf_path.name}: {'; '.join(errors)}"
        ) from exc


def _extract_with_fitz(pdf_path: Path) -> tuple[str, int, str]:
    import fitz

    parts: list[str] = []
    with fitz.open(pdf_path) as doc:
        page_count = len(doc)
        if page_count == 0:
            raise ValueError("PDF has no pages")
        for page in doc:
            page_text = page.get_text()
            if page_text and page_text.strip():
                parts.append(page_text.strip())
    return " ".join(parts).strip(), page_count, "pymupdf"


def _extract_with_pdfplumber(pdf_path: Path) -> tuple[str, int, str]:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        if page_count == 0:
            raise ValueError("PDF has no pages")
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                parts.append(page_text.strip())
    return " ".join(parts).strip(), page_count, "pdfplumber"


def _extract_with_pypdf(pdf_path: Path) -> tuple[str, int, str]:
    from pypdf import PdfReader

    parts: list[str] = []
    with open(pdf_path, "rb") as handle:
        reader = PdfReader(handle)
        page_count = len(reader.pages)
        if page_count == 0:
            raise ValueError("PDF has no pages")
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                parts.append(page_text.strip())
    return " ".join(parts).strip(), page_count, "pypdf"


def _pdf_page_count_safe(pdf_path: Path) -> int:
    try:
        _, count, _ = _direct_extract_pdf(pdf_path)
        return count
    except Exception:
        try:
            from pypdf import PdfReader

            with open(pdf_path, "rb") as handle:
                return len(PdfReader(handle).pages)
        except Exception:
            return 1


def _run_ocr_primary(pdf_path: Path) -> str:
    """Run configured primary OCR (default: pytesseract)."""
    if config.OCR_PRIMARY == "tesseract":
        return _run_with_timeout(
            lambda: _tesseract_ocr(pdf_path),
            config.OCR_TIMEOUT_SECONDS,
            label="tesseract",
        )
    return _run_with_timeout(
        lambda: _tesseract_ocr(pdf_path),
        config.OCR_TIMEOUT_SECONDS,
        label="tesseract",
    )


def _run_ocr_fallback(pdf_path: Path) -> str:
    """Run easyocr as fallback OCR engine."""
    return _run_with_timeout(
        lambda: _easyocr_ocr(pdf_path),
        config.OCR_TIMEOUT_SECONDS,
        label="easyocr",
    )


def _tesseract_ocr(pdf_path: Path, dpi: int = 150, lang: str = "eng") -> str:
    import pytesseract
    from pdf2image import convert_from_path

    pytesseract.get_tesseract_version()
    images = convert_from_path(pdf_path, dpi=dpi, fmt="png", thread_count=2)
    if not images:
        raise ValueError("pdf2image produced no pages")

    parts: list[str] = []
    for index, image in enumerate(images):
        try:
            page_text = pytesseract.image_to_string(image, lang=lang)
            if page_text and page_text.strip():
                parts.append(page_text.strip())
        except Exception as exc:
            logger.warning("Tesseract failed on page %d of %s: %s", index + 1, pdf_path.name, exc)

    if not parts:
        raise ValueError("Tesseract OCR produced no text")
    return " ".join(parts).strip()


def _easyocr_ocr(pdf_path: Path, dpi: int = 150) -> str:
    try:
        import easyocr
        import numpy as np
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise ValueError("easyocr is not installed") from exc

    images = convert_from_path(pdf_path, dpi=dpi, fmt="png", thread_count=2)
    if not images:
        raise ValueError("pdf2image produced no pages")

    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    parts: list[str] = []
    for index, image in enumerate(images):
        try:
            lines = reader.readtext(np.array(image), detail=0, paragraph=True)
            page_text = " ".join(line.strip() for line in lines if line and line.strip())
            if page_text:
                parts.append(page_text)
        except Exception as exc:
            logger.warning("EasyOCR failed on page %d of %s: %s", index + 1, pdf_path.name, exc)

    if not parts:
        raise ValueError("EasyOCR produced no text")
    return " ".join(parts).strip()


def _run_with_timeout(
    fn: Callable[[], str],
    timeout_seconds: int,
    label: str,
) -> str:
    """Execute ``fn`` in a worker thread with a hard timeout."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            raise TimeoutError(f"{label} OCR exceeded {timeout_seconds}s") from exc


def _build_result(
    *,
    text: str,
    method: str,
    char_count: int,
    ocr_triggered: bool,
    state: ExtractionState,
    latency_ms: float,
    failure_reason: Optional[str] = None,
) -> TypeExtractionResult:
    result: TypeExtractionResult = {
        "text": text,
        "method": method,
        "char_count": char_count,
        "ocr_triggered": ocr_triggered,
        "state": state.value,
        "latency_ms": round(latency_ms, 3),
    }
    if failure_reason:
        result["failure_reason"] = failure_reason
    return result


def _log_state(filename: str, state: ExtractionState) -> None:
    logger.info("resume=%s state=%s", filename, state.value)


def _log_extraction(
    filename: str,
    result: TypeExtractionResult,
    *,
    direct_backend: Optional[str] = None,
    ocr_ms: Optional[float] = None,
) -> None:
    extra = ""
    if direct_backend:
        extra = f" backend={direct_backend}"
    if ocr_ms is not None:
        extra += f" ocr_ms={ocr_ms:.1f}"
    failure = result.get("failure_reason")
    failure_part = f" failure_reason={failure}" if failure else ""
    logger.info(
        "resume=%s method=%s chars=%d ocr_triggered=%s state=%s latency_ms=%.1f%s%s",
        filename,
        result["method"],
        result["char_count"],
        result["ocr_triggered"],
        result["state"],
        result["latency_ms"],
        extra,
        failure_part,
    )
