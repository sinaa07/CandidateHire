"""V2 company dashboard route."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_verified_company
from app.api.routes.v2.helpers import jobs_to_summary_list
from app.db.session import get_db
from app.models.schemas import (
    DashboardCompany,
    DashboardResponse,
    DashboardSummary,
)
from app.models.tables import Candidate, CandidateIndex, Company, Job, Ranking

router = APIRouter(
    prefix="/api/v2/companies/{company_id}",
    tags=["v2-dashboard"],
    dependencies=[Depends(get_verified_company)],
)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    company: Company = Depends(get_verified_company),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    company_id = company.id

    jobs = db.execute(
        select(Job)
        .where(Job.company_id == company_id, Job.status != "deleted")
        .order_by(Job.updated_at.desc())
    ).scalars().all()
    job_ids = [j.id for j in jobs]

    total_jobs = len(jobs)
    open_jobs = sum(1 for j in jobs if j.status == "open")

    total_candidates = 0
    indexed_candidates = 0
    ranked_candidates = 0

    if job_ids:
        total_candidates = db.scalar(
            select(func.count(Candidate.id)).where(Candidate.job_id.in_(job_ids))
        ) or 0

        indexed_candidates = db.scalar(
            select(func.count(CandidateIndex.id)).where(CandidateIndex.job_id.in_(job_ids))
        ) or 0

        ranked_candidates = db.scalar(
            select(func.count(func.distinct(Ranking.candidate_id))).where(
                Ranking.job_id.in_(job_ids)
            )
        ) or 0

    return DashboardResponse(
        company=DashboardCompany(
            id=company.id,
            name=company.name,
            settings=company.settings or {},
        ),
        summary=DashboardSummary(
            total_jobs=total_jobs,
            open_jobs=open_jobs,
            total_candidates=total_candidates,
            indexed_candidates=indexed_candidates,
            ranked_candidates=ranked_candidates,
        ),
        jobs=jobs_to_summary_list(db, list(jobs)),
    )
