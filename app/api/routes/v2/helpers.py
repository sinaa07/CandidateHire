"""Shared helpers for v2 company/job routes."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.schemas import JobRead, JobSummary
from app.models.tables import Candidate, CandidateIndex, Job, Ranking, _default_ranking_config


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or str(uuid.uuid4())


def merge_ranking_config(override: dict[str, Any] | None) -> dict[str, Any]:
    base = _default_ranking_config()
    if not override:
        return base
    merged = {**base, **override}
    if "weights" in override:
        merged["weights"] = {**base["weights"], **override["weights"]}
    if "hard_filters" in override:
        merged["hard_filters"] = {**base["hard_filters"], **override["hard_filters"]}
    return merged


def company_storage_path(company_id: uuid.UUID) -> str:
    return f"storage/companies/{company_id}"


def job_storage_path(company_id: uuid.UUID, job_id: uuid.UUID) -> str:
    return f"{company_storage_path(company_id)}/jobs/{job_id}"


def create_job_storage_dirs(company_id: uuid.UUID, job_id: uuid.UUID) -> None:
    from pathlib import Path

    root = Path(job_storage_path(company_id, job_id))
    for sub in (
        "jd",
        "resumes/raw",
        "resumes/processed",
        "embeddings",
        "rankings",
        "rag",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)


class JobStats:
    resume_count: int = 0
    indexed_count: int = 0
    top_score: float | None = None
    pipeline_stage: str = "uploaded"
    last_ranked_at: datetime | None = None


def _fetch_job_stats(db: Session, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, JobStats]:
    if not job_ids:
        return {}

    stats: dict[uuid.UUID, JobStats] = {jid: JobStats() for jid in job_ids}

    resume_rows = db.execute(
        select(Candidate.job_id, func.count(Candidate.id))
        .where(Candidate.job_id.in_(job_ids))
        .group_by(Candidate.job_id)
    ).all()
    for job_id, count in resume_rows:
        stats[job_id].resume_count = count

    indexed_rows = db.execute(
        select(CandidateIndex.job_id, func.count(CandidateIndex.id))
        .where(CandidateIndex.job_id.in_(job_ids))
        .group_by(CandidateIndex.job_id)
    ).all()
    for job_id, count in indexed_rows:
        stats[job_id].indexed_count = count

    ranking_rows = db.execute(
        select(
            Ranking.job_id,
            func.max(Ranking.final_score),
            func.max(Ranking.ranked_at),
            func.count(Ranking.id),
        )
        .where(Ranking.job_id.in_(job_ids))
        .group_by(Ranking.job_id)
    ).all()
    for job_id, top_score, last_ranked_at, rank_count in ranking_rows:
        s = stats[job_id]
        s.top_score = top_score
        s.last_ranked_at = last_ranked_at
        if rank_count > 0:
            s.pipeline_stage = "ranked"

    for job_id, s in stats.items():
        if s.pipeline_stage != "ranked" and s.indexed_count > 0:
            s.pipeline_stage = "indexed"

    return stats


def job_to_read(db: Session, job: Job) -> JobRead:
    stats_map = _fetch_job_stats(db, [job.id])
    s = stats_map.get(job.id, JobStats())
    return JobRead(
        id=job.id,
        company_id=job.company_id,
        title=job.title,
        department=job.department,
        status=job.status,
        jd_text=job.jd_text,
        jd_file_path=job.jd_file_path,
        ranking_config=job.ranking_config,
        created_at=job.created_at,
        updated_at=job.updated_at,
        resume_count=s.resume_count,
        indexed_count=s.indexed_count,
        top_score=s.top_score,
        pipeline_stage=s.pipeline_stage,
        last_ranked_at=s.last_ranked_at,
    )


def job_to_summary(db: Session, job: Job) -> JobSummary:
    stats_map = _fetch_job_stats(db, [job.id])
    s = stats_map.get(job.id, JobStats())
    return JobSummary(
        id=job.id,
        title=job.title,
        status=job.status,
        department=job.department,
        created_at=job.created_at,
        updated_at=job.updated_at,
        resume_count=s.resume_count,
        indexed_count=s.indexed_count,
        top_score=s.top_score,
        pipeline_stage=s.pipeline_stage,
        last_ranked_at=s.last_ranked_at,
    )


def jobs_to_read_list(db: Session, jobs: list[Job]) -> list[JobRead]:
    if not jobs:
        return []
    job_ids = [j.id for j in jobs]
    stats_map = _fetch_job_stats(db, job_ids)
    result: list[JobRead] = []
    for job in jobs:
        s = stats_map.get(job.id, JobStats())
        result.append(
            JobRead(
                id=job.id,
                company_id=job.company_id,
                title=job.title,
                department=job.department,
                status=job.status,
                jd_text=job.jd_text,
                jd_file_path=job.jd_file_path,
                ranking_config=job.ranking_config,
                created_at=job.created_at,
                updated_at=job.updated_at,
                resume_count=s.resume_count,
                indexed_count=s.indexed_count,
                top_score=s.top_score,
                pipeline_stage=s.pipeline_stage,
                last_ranked_at=s.last_ranked_at,
            )
        )
    return result


def jobs_to_summary_list(db: Session, jobs: list[Job]) -> list[JobSummary]:
    if not jobs:
        return []
    job_ids = [j.id for j in jobs]
    stats_map = _fetch_job_stats(db, job_ids)
    return [
        JobSummary(
            id=job.id,
            title=job.title,
            status=job.status,
            department=job.department,
            created_at=job.created_at,
            updated_at=job.updated_at,
            resume_count=stats_map.get(job.id, JobStats()).resume_count,
            indexed_count=stats_map.get(job.id, JobStats()).indexed_count,
            top_score=stats_map.get(job.id, JobStats()).top_score,
            pipeline_stage=stats_map.get(job.id, JobStats()).pipeline_stage,
            last_ranked_at=stats_map.get(job.id, JobStats()).last_ranked_at,
        )
        for job in jobs
    ]
