"""V2 resume upload and management for a job."""
from __future__ import annotations

import logging
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_verified_company
from app.api.routes.v2.helpers import create_job_storage_dirs, job_storage_path
from app.db.session import get_db
from app.models.tables import Candidate, Job

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/companies/{company_id}/jobs/{job_id}/resumes",
    tags=["v2-resumes"],
    dependencies=[Depends(get_verified_company)],
)

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}
ZIP_SKIP_PREFIXES = ("._", "~$")
ZIP_SKIP_NAMES = {".DS_Store", "Thumbs.db"}


def _get_job_or_404(db: Session, company_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.execute(
        select(Job).where(Job.id == job_id, Job.company_id == company_id)
    ).scalar_one_or_none()
    if job is None or job.status == "deleted":
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _raw_dir(company_id: uuid.UUID, job_id: uuid.UUID) -> Path:
    return Path(job_storage_path(company_id, job_id)) / "resumes" / "raw"


def _is_allowed_resume(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES


def _should_skip_zip_member(member: str) -> bool:
    name = Path(member).name
    if member.endswith("/"):
        return True
    if name in ZIP_SKIP_NAMES:
        return True
    if any(name.startswith(prefix) for prefix in ZIP_SKIP_PREFIXES):
        return True
    return False


def _resolve_unique_path(raw_dir: Path, filename: str) -> Path:
    safe_name = Path(filename).name
    dest = raw_dir / safe_name
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    counter = 2
    while True:
        candidate = raw_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


async def _extract_zip_to_raw(
    zip_file: UploadFile,
    raw_dir: Path,
    job_root: Path,
) -> tuple[list[Path], int]:
    temp_zip = job_root / "_upload_temp.zip"
    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    skipped = 0
    try:
        content = await zip_file.read()
        temp_zip.write_bytes(content)
        with zipfile.ZipFile(temp_zip, "r") as zf:
            for member in zf.namelist():
                if _should_skip_zip_member(member):
                    continue
                try:
                    zf.extract(member, raw_dir)
                except Exception as exc:
                    logger.warning("Failed to extract %s: %s", member, exc)
                    skipped += 1
                    continue
                out_path = raw_dir / member
                if not out_path.is_file():
                    continue
                if _is_allowed_resume(out_path):
                    extracted.append(out_path)
                else:
                    skipped += 1
                    logger.warning("Skipping unsupported file in ZIP: %s", member)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="Invalid ZIP file") from exc
    finally:
        if temp_zip.exists():
            temp_zip.unlink()

    return extracted, skipped


async def _save_upload_files(
    uploads: list[UploadFile],
    raw_dir: Path,
) -> tuple[list[Path], int]:
    saved: list[Path] = []
    skipped = 0
    raw_dir.mkdir(parents=True, exist_ok=True)
    for upload in uploads:
        if not upload.filename:
            continue
        filename = Path(upload.filename).name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            skipped += 1
            logger.warning("Skipping unsupported upload: %s", filename)
            continue
        dest = _resolve_unique_path(raw_dir, filename)
        dest.write_bytes(await upload.read())
        saved.append(dest)
    return saved, skipped


def _register_candidates(
    db: Session,
    paths: list[Path],
    raw_dir: Path,
    company_id: uuid.UUID,
    job_id: uuid.UUID,
) -> tuple[int, int, list[dict]]:
    uploaded = 0
    skipped = 0
    created: list[dict] = []
    seen: set[str] = set()

    for path in paths:
        if not _is_allowed_resume(path):
            skipped += 1
            logger.warning("Skipping unsupported file: %s", path)
            continue

        original_name = path.name
        if path.parent != raw_dir:
            dest = _resolve_unique_path(raw_dir, original_name)
            if dest.resolve() != path.resolve():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), dest)
                path = dest
                original_name = path.name

        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)

        record = Candidate(
            job_id=job_id,
            company_id=company_id,
            original_filename=original_name,
            file_path=str(path),
            status="uploaded",
        )
        db.add(record)
        db.flush()
        uploaded += 1
        created.append(
            {
                "id": str(record.id),
                "filename": original_name,
                "status": record.status,
            }
        )

    return uploaded, skipped, created


@router.post("/")
async def upload_resumes(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    files: list[UploadFile] = File(default=[]),
    zip_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> dict:
    _get_job_or_404(db, company_id, job_id)

    has_files = bool(files) and any(f.filename for f in files)
    has_zip = zip_file is not None and bool(zip_file.filename)
    if not has_files and not has_zip:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one of: files, zip_file",
        )

    create_job_storage_dirs(company_id, job_id)
    raw_dir = _raw_dir(company_id, job_id)
    job_root = Path(job_storage_path(company_id, job_id))

    paths_to_register: list[Path] = []
    skipped = 0

    if has_zip:
        zip_paths, zip_skipped = await _extract_zip_to_raw(zip_file, raw_dir, job_root)
        paths_to_register.extend(zip_paths)
        skipped += zip_skipped

    if has_files:
        saved, file_skipped = await _save_upload_files(files, raw_dir)
        paths_to_register.extend(saved)
        skipped += file_skipped

    if not paths_to_register:
        raise HTTPException(
            status_code=422,
            detail="No valid resume files found (PDF, DOCX, TXT only)",
        )

    uploaded, reg_skipped, candidates = _register_candidates(
        db, paths_to_register, raw_dir, company_id, job_id
    )
    skipped += reg_skipped

    db.commit()

    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "candidates": candidates,
        "job_id": str(job_id),
    }


@router.get("/")
def list_resumes(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    _get_job_or_404(db, company_id, job_id)

    candidates = db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.index_row),
            selectinload(Candidate.rankings),
        )
        .where(Candidate.job_id == job_id, Candidate.company_id == company_id)
        .order_by(Candidate.created_at.desc())
    ).scalars().all()

    result: list[dict] = []
    for candidate in candidates:
        index_row = candidate.index_row
        indexed = index_row is not None
        ranked = bool(candidate.rankings)

        index_summary = None
        if index_row is not None:
            index_summary = {
                "skills": index_row.normalized_skills or [],
                "experience_years": index_row.total_experience_years,
                "education_tier": index_row.education_tier,
            }

        result.append(
            {
                "id": str(candidate.id),
                "filename": candidate.original_filename,
                "status": candidate.status,
                "created_at": candidate.created_at,
                "indexed": indexed,
                "ranked": ranked,
                "index_summary": index_summary,
            }
        )

    return result


@router.delete("/{candidate_id}")
def delete_resume(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _get_job_or_404(db, company_id, job_id)

    candidate = db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.job_id == job_id,
            Candidate.company_id == company_id,
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    for path_str in (candidate.file_path, candidate.processed_text_path):
        if path_str:
            path = Path(path_str)
            if path.is_file():
                path.unlink(missing_ok=True)

    embeddings_path = (
        Path(job_storage_path(company_id, job_id)) / "embeddings" / f"{candidate_id}.npy"
    )
    if embeddings_path.is_file():
        embeddings_path.unlink()

    db.delete(candidate)
    db.commit()
    return {"success": True}
