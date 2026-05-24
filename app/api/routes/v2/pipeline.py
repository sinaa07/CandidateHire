"""V2 indexing, ranking pipeline triggers and status."""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_verified_company
from app.api.routes.v2.jobs import _get_job_or_404
from app.db.session import SessionLocal, get_db
from app.models.tables import Candidate, Ranking
from app.services.v2.indexing_service import index_candidate
from app.services.v2.ranking_service import rank_job
from app.services.v2.reranking_service import rerank

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/companies/{company_id}/jobs/{job_id}/pipeline",
    tags=["v2-pipeline"],
    dependencies=[Depends(get_verified_company)],
)


def _run_index_candidate_task(candidate_id: uuid.UUID) -> None:
    """Background wrapper: own DB session per candidate."""
    db = SessionLocal()
    try:
        asyncio.run(index_candidate(str(candidate_id), db))
    except Exception:
        logger.exception("Background indexing task crashed for %s", candidate_id)
    finally:
        db.close()


@router.post("/index")
def start_indexing(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    _get_job_or_404(db, company_id, job_id)

    candidates = db.execute(
        select(Candidate).where(
            Candidate.job_id == job_id,
            Candidate.company_id == company_id,
            Candidate.status == "uploaded",
        )
    ).scalars().all()

    for candidate in candidates:
        background_tasks.add_task(_run_index_candidate_task, candidate.id)

    return {"message": "Indexing started", "queued": len(candidates)}


@router.get("/status")
def indexing_status(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, int | bool]:
    _get_job_or_404(db, company_id, job_id)

    rows = db.execute(
        select(Candidate.status, func.count(Candidate.id))
        .where(Candidate.job_id == job_id, Candidate.company_id == company_id)
        .group_by(Candidate.status)
    ).all()

    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    uploaded = counts.get("uploaded", 0)
    processing = counts.get("processing", 0)
    processed = counts.get("processed", 0)
    failed = counts.get("failed", 0)
    duplicate = counts.get("duplicate", 0)

    return {
        "total": total,
        "uploaded": uploaded,
        "processing": processing,
        "processed": processed,
        "failed": failed,
        "duplicate": duplicate,
        "indexing_complete": uploaded == 0 and processing == 0,
    }


class RankRequest(BaseModel):
    config_override: dict[str, Any] | None = None


class RerankRequest(BaseModel):
    weights: dict[str, float] = Field(
        ...,
        description="semantic, skill_match, experience, education (sum ~1.0)",
    )


@router.post("/rank")
async def run_ranking(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    body: RankRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_job_or_404(db, company_id, job_id)

    try:
        result = await rank_job(
            str(job_id),
            str(company_id),
            config_override=body.config_override if body else None,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@router.post("/rerank")
def run_reranking(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    body: RerankRequest,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    _get_job_or_404(db, company_id, job_id)

    try:
        return rerank(str(job_id), body.weights, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/rankings")
def list_rankings(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    passed_only: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_job_or_404(db, company_id, job_id)

    filters = [
        Ranking.job_id == job_id,
        Ranking.company_id == company_id,
        Ranking.final_score >= min_score,
    ]
    if passed_only:
        filters.append(Ranking.passed_hard_filter.is_(True))

    total = db.scalar(select(func.count(Ranking.id)).where(*filters)) or 0

    rows = db.execute(
        select(Ranking, Candidate)
        .join(Candidate, Candidate.id == Ranking.candidate_id)
        .where(*filters)
        .order_by(Ranking.rank_position.asc())
        .limit(limit)
        .offset(offset)
    ).all()

    items = []
    for ranking, candidate in rows:
        items.append(
            {
                "candidate_id": str(ranking.candidate_id),
                "filename": candidate.original_filename,
                "rank_position": ranking.rank_position,
                "final_score": ranking.final_score,
                "score_breakdown": {
                    "semantic": ranking.semantic_score,
                    "skill_match": ranking.skill_score,
                    "experience": ranking.experience_score,
                    "education": ranking.education_score,
                },
                "matched_skills": ranking.matched_skills or [],
                "missing_skills": ranking.missing_skills or [],
                "top_matching_chunks": ranking.top_matching_chunks or [],
                "passed_hard_filter": ranking.passed_hard_filter,
                "ranked_at": ranking.ranked_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/rankings/export")
def export_rankings_csv(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    _get_job_or_404(db, company_id, job_id)

    rows = db.execute(
        select(Ranking, Candidate)
        .join(Candidate, Candidate.id == Ranking.candidate_id)
        .where(Ranking.job_id == job_id, Ranking.company_id == company_id)
        .order_by(Ranking.rank_position.asc())
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "rank_position",
            "filename",
            "final_score",
            "semantic",
            "skill_match",
            "experience",
            "education",
            "passed_hard_filter",
        ]
    )
    for ranking, candidate in rows:
        writer.writerow(
            [
                ranking.rank_position,
                candidate.original_filename,
                ranking.final_score,
                ranking.semantic_score,
                ranking.skill_score,
                ranking.experience_score,
                ranking.education_score,
                ranking.passed_hard_filter,
            ]
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="rankings_{job_id}.csv"'},
    )
