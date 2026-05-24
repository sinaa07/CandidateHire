"""V2 job management routes."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_verified_company
from app.db.session import get_db
from app.models.schemas import JobRead, JobUpdate
from app.models.tables import Job
from app.api.routes.v2.helpers import (
    create_job_storage_dirs,
    job_storage_path,
    job_to_read,
    jobs_to_read_list,
    merge_ranking_config,
)
from app.utils.text_extraction import extract_text

router = APIRouter(
    prefix="/api/v2/companies/{company_id}/jobs",
    tags=["v2-jobs"],
    dependencies=[Depends(get_verified_company)],
)


def _get_job_or_404(db: Session, company_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.execute(
        select(Job).where(Job.id == job_id, Job.company_id == company_id)
    ).scalar_one_or_none()
    if job is None or job.status == "deleted":
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _save_jd_file(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    jd_file: UploadFile,
) -> tuple[str, str]:
    job_root = Path(job_storage_path(company_id, job_id))
    jd_dir = job_root / "jd"
    jd_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(jd_file.filename or "jd_upload").name
    dest = jd_dir / filename
    content = await jd_file.read()
    dest.write_bytes(content)
    text = extract_text(dest)
    return text, str(dest)


@router.post("/", response_model=JobRead, status_code=201)
async def create_job(
    company_id: uuid.UUID,
    title: str = Form(...),
    department: str | None = Form(None),
    status: str = Form("open"),
    jd_text: str | None = Form(None),
    ranking_config: str | None = Form(None),
    jd_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> JobRead:
    parsed_config: dict | None = None
    if ranking_config:
        try:
            parsed_config = json.loads(ranking_config)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="ranking_config must be valid JSON") from exc

    jd_text_value = jd_text.strip() if jd_text and jd_text.strip() else None
    jd_file_path: str | None = None

    if not jd_text_value and jd_file is None:
        raise HTTPException(
            status_code=422,
            detail="Either jd_text or jd_file must be provided non-empty.",
        )

    job = Job(
        company_id=company_id,
        title=title.strip(),
        department=department,
        status=status,
        jd_text=jd_text_value,
        ranking_config=merge_ranking_config(parsed_config),
    )
    db.add(job)
    db.flush()

    create_job_storage_dirs(company_id, job.id)

    if jd_file is not None and jd_file.filename:
        try:
            extracted, jd_file_path = await _save_jd_file(company_id, job.id, jd_file)
            job.jd_text = extracted or jd_text_value
            job.jd_file_path = jd_file_path
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=422, detail=f"Failed to process jd_file: {exc}") from exc
    elif not job.jd_text:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="Either jd_text or jd_file must be provided non-empty.",
        )

    db.commit()
    db.refresh(job)
    return job_to_read(db, job)


@router.get("/", response_model=list[JobRead])
def list_jobs(company_id: uuid.UUID, db: Session = Depends(get_db)) -> list[JobRead]:
    jobs = db.execute(
        select(Job)
        .where(Job.company_id == company_id, Job.status != "deleted")
        .order_by(Job.created_at.desc())
    ).scalars().all()
    return jobs_to_read_list(db, list(jobs))


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, company_id, job_id)
    return job_to_read(db, job)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    body: JobUpdate,
    db: Session = Depends(get_db),
) -> JobRead:
    job = _get_job_or_404(db, company_id, job_id)

    updates = body.model_dump(exclude_unset=True)
    if "ranking_config" in updates and updates["ranking_config"] is not None:
        updates["ranking_config"] = merge_ranking_config(updates["ranking_config"])
    if "jd_text" in updates and updates["jd_text"] is not None:
        updates["jd_text"] = updates["jd_text"].strip() or None

    for field, value in updates.items():
        setattr(job, field, value)
    job.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)
    return job_to_read(db, job)


@router.delete("/{job_id}")
def delete_job(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    job = _get_job_or_404(db, company_id, job_id)
    job.status = "deleted"
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}
