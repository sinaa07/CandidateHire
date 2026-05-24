"""
Single-resume processing worker.

Invoked by the Phase-2 multiprocessing pool (or sequentially for small batches).
Uses smart OCR gating for PDFs and never raises unhandled exceptions.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.models.enums import ExtractionState, ResumeStatus
from app.services.ocr_service import extract_pdf_resume
from app.services.resume_intelligence import extract_resume_intelligence
from app.utils.hashing import compute_sha256
from app.utils.latency_tracker import LatencyRecorder, STAGE_DB_WRITES
from app.utils.text_extraction import extract_text
from app.utils.validation import validate_text

logger = logging.getLogger(__name__)


def process_resume_file(args: Tuple[Path, Path, Dict]) -> Dict[str, Any]:
    """
    Process one resume file: extract text, validate, dedupe, persist artifacts.

    Args:
        args: ``(resume_file, processed_dir, shared_hash_registry)``

    Returns:
        Result dict including filename, status, reason, content_hash, extraction
        metadata, and latency samples.
    """
    resume_file, processed_dir, shared_hash_registry = args
    filename = resume_file.name
    result: Dict[str, Any] = {
        "filename": filename,
        "status": None,
        "reason": None,
        "content_hash": None,
        "duplicate_of": None,
        "latency_samples": None,
        "extraction": None,
    }
    recorder = LatencyRecorder()

    try:
        text, extraction_meta = _extract_resume_text(resume_file, recorder)
        result["extraction"] = extraction_meta

        status = validate_text(text)
        if status == ResumeStatus.EMPTY:
            ocr_state = (extraction_meta or {}).get("state")
            if ocr_state == ExtractionState.OCR_FAILED.value:
                result["status"] = ResumeStatus.EMPTY
                result["reason"] = (extraction_meta or {}).get(
                    "failure_reason",
                    "OCR failed; no extractable text",
                )
            else:
                result["status"] = ResumeStatus.EMPTY
                result["reason"] = "No extractable text (file may be image-based, corrupted, or empty)"
        elif status == ResumeStatus.OK:
            content_hash = compute_sha256(text)
            result["content_hash"] = content_hash

            if content_hash in shared_hash_registry:
                result["status"] = ResumeStatus.DUPLICATE
                result["reason"] = f"Duplicate of {shared_hash_registry[content_hash]}"
                result["duplicate_of"] = shared_hash_registry[content_hash]
            else:
                shared_hash_registry[content_hash] = filename
                result["status"] = ResumeStatus.OK

                output_file = processed_dir / f"{resume_file.name}.txt"
                with recorder.stage(STAGE_DB_WRITES):
                    output_file.write_text(text, encoding="utf-8")

                try:
                    intelligence = extract_resume_intelligence(text, filename, recorder=recorder)
                    base_name = output_file.stem
                    sections_file = processed_dir / f"{base_name}_sections.json"
                    entities_file = processed_dir / f"{base_name}_entities.json"
                    experience_file = processed_dir / f"{base_name}_experience.json"
                    with recorder.stage(STAGE_DB_WRITES):
                        sections_file.write_text(
                            json.dumps(intelligence["sections"], indent=2),
                            encoding="utf-8",
                        )
                        entities_file.write_text(
                            json.dumps(intelligence["entities"], indent=2),
                            encoding="utf-8",
                        )
                        experience_file.write_text(
                            json.dumps(intelligence["experience"], indent=2),
                            encoding="utf-8",
                        )
                except Exception as exc:
                    logger.warning("Failed to extract intelligence for %s: %s", filename, exc)
                    result["status"] = ResumeStatus.FAILED
                    result["reason"] = f"Intelligence extraction failed: {exc}"
        else:
            result["status"] = status
            result["reason"] = "Validation failed"

    except KeyboardInterrupt:
        logger.warning("Processing interrupted for %s", filename)
        raise
    except Exception as exc:
        result["status"] = ResumeStatus.FAILED
        error_msg = str(exc)
        if "Unsupported file type" in error_msg:
            result["reason"] = (
                f"Unsupported format: {resume_file.suffix} (supported: .pdf, .docx, .txt)"
            )
        elif "Failed to extract text" in error_msg:
            result["reason"] = f"Extraction error: {error_msg}"
        elif "timeout" in error_msg.lower():
            result["reason"] = f"Processing timeout: {error_msg}"
        else:
            result["reason"] = f"Processing failed: {error_msg}"
        logger.error("Failed to process %s: %s", filename, exc, exc_info=True)

    result["latency_samples"] = recorder.to_samples_dict()
    return result


def _extract_resume_text(
    file_path: Path,
    recorder: LatencyRecorder,
) -> tuple[str, Optional[Dict[str, Any]]]:
    """
    Extract plain text; PDFs use smart OCR gating via ``ocr_service``.

    Returns:
        Tuple of (text, extraction_metadata or None for non-PDF).
    """
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        meta = extract_pdf_resume(file_path, recorder=recorder)
        return meta.get("text", ""), meta
    text = extract_text(file_path, use_ocr_fallback=False, recorder=recorder)
    return text, None
