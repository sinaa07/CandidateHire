"""V2 indexing, ranking pipeline triggers and status."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_verified_company
from app.api.routes.v2.helpers import job_storage_path
from app.api.routes.v2.jobs import _get_job_or_404
from app.db.session import SessionLocal, get_db
from app.models.schemas import SkillMapStatus
from app.models.tables import Candidate, Ranking
from app.services.llm_service import get_available_providers
from app.services.v2.indexing_service import index_candidate
from app.services.v2.ranking_service import rank_job
from app.services.v2.reranking_service import rerank
from app.services.v2.skill_coverage_service import run_build_skill_implied_by_map_task

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/companies/{company_id}/jobs/{job_id}/pipeline",
    tags=["v2-pipeline"],
    dependencies=[Depends(get_verified_company)],
)


def _llm_configured() -> bool:
    return bool(get_available_providers())


def _skill_maps_dir(company_id: uuid.UUID, job_id: uuid.UUID) -> Path:
    return Path(job_storage_path(company_id, job_id)) / "skill_maps"


def _load_build_meta(company_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any]:
    meta_path = _skill_maps_dir(company_id, job_id) / "build_meta.json"
    if not meta_path.exists():
        return {}
    try:
        with meta_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


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
    ranking_mode: Literal["keyword", "contextual"] | None = None


class RerankRequest(BaseModel):
    weights: dict[str, float] = Field(
        ...,
        description="semantic, skill_match, experience, education (sum ~1.0)",
    )


@router.get("/skill-map/status", response_model=SkillMapStatus)
def skill_map_status(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SkillMapStatus:
    job = _get_job_or_404(db, company_id, job_id)
    meta = _load_build_meta(company_id, job_id)

    return SkillMapStatus(
        job_id=str(job_id),
        ranking_mode=job.ranking_mode or "keyword",
        status=job.skill_map_status or "pending",
        built_at=job.skill_map_built_at,
        error=job.skill_map_error,
        skill_count=meta.get("skill_count"),
        implied_skills_total=meta.get("implied_skills_total"),
    )


@router.get("/skill-map")
def get_skill_map(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job = _get_job_or_404(db, company_id, job_id)

    if job.skill_map_status == "building":
        raise HTTPException(
            status_code=503,
            detail="Skill map is being built, try again in a few seconds",
        )

    if job.skill_map_status != "ready" or not job.skill_implied_by_map_path:
        raise HTTPException(status_code=404, detail="Skill map not ready")

    map_path = Path(job.skill_implied_by_map_path)
    if not map_path.exists():
        raise HTTPException(status_code=404, detail="Skill map not ready")

    meta = _load_build_meta(company_id, job_id)
    with map_path.open(encoding="utf-8") as f:
        skill_implied_by_map = json.load(f)

    return {
        "job_id": str(job_id),
        "built_at": meta.get("built_at") or (
            job.skill_map_built_at.isoformat() if job.skill_map_built_at else None
        ),
        "model_used": meta.get("model_used"),
        "skill_implied_by_map": skill_implied_by_map,
    }


@router.post("/skill-map/rebuild")
def rebuild_skill_map(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    job = _get_job_or_404(db, company_id, job_id)

    if not (job.jd_text or "").strip():
        raise HTTPException(status_code=400, detail="Job has no JD text")

    if not _llm_configured():
        raise HTTPException(
            status_code=400,
            detail="No LLM API key configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY)",
        )

    job.skill_map_status = "pending"
    job.skill_map_error = None
    db.commit()

    background_tasks.add_task(
        run_build_skill_implied_by_map_task,
        str(job_id),
        str(company_id),
    )

    return {"message": "Rebuild started", "job_id": str(job_id)}


@router.post("/rank")
async def run_ranking(
    company_id: uuid.UUID,
    job_id: uuid.UUID,
    body: RankRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job = _get_job_or_404(db, company_id, job_id)

    effective_mode = (
        body.ranking_mode if body and body.ranking_mode else job.ranking_mode or "keyword"
    )
    if effective_mode == "contextual" and job.skill_map_status != "ready":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "skill_map_not_ready",
                "message": (
                    "Contextual ranking requires skill map to be built first. "
                    "Check /skill-map/status and retry when status is ready."
                ),
                "skill_map_status": job.skill_map_status,
            },
        )

    try:
        result = await rank_job(
            str(job_id),
            str(company_id),
            config_override=body.config_override if body else None,
            db=db,
            ranking_mode_override=body.ranking_mode if body else None,
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
    mode_filter: Literal["keyword", "contextual"] | None = Query(None),
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
    if mode_filter is not None:
        filters.append(Ranking.ranking_mode_used == mode_filter)

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
                "truly_missing_skills": ranking.truly_missing_skills,
                "likely_covered_skills": ranking.likely_covered_skills,
                "ranking_mode_used": ranking.ranking_mode_used,
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
