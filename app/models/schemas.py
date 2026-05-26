"""Pydantic v2 schemas for multi-tenant API payloads."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    api_key: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    api_key: str
    created_at: datetime
    settings: dict[str, Any]


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1)
    jd_text: str | None = None
    jd_file_path: str | None = None
    department: str | None = None
    status: str = "open"
    ranking_config: dict[str, Any] | None = None
    ranking_mode: str = "keyword"

    @model_validator(mode="after")
    def jd_source_present(self):
        text_ok = self.jd_text is not None and bool(self.jd_text.strip())
        path_ok = self.jd_file_path is not None and bool(self.jd_file_path.strip())
        if not text_ok and not path_ok:
            raise ValueError("Either jd_text or jd_file must be provided non-empty.")
        return self


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    department: str | None
    status: str
    jd_text: str | None
    jd_file_path: str | None
    ranking_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    resume_count: int = 0
    indexed_count: int = 0
    top_score: float | None = None
    pipeline_stage: str = "uploaded"
    last_ranked_at: datetime | None = None
    ranking_mode: str = "keyword"
    skill_map_status: str = "pending"
    skill_map_built_at: datetime | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    status: str | None = None
    jd_text: str | None = None
    jd_file_path: str | None = None
    ranking_config: dict[str, Any] | None = None
    ranking_mode: str | None = None


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    company_id: uuid.UUID
    original_filename: str
    file_path: str
    processed_text_path: str | None
    content_hash: str | None
    status: str
    parse_error: str | None
    created_at: datetime


class ScoreBreakdown(BaseModel):
    semantic: float | None = None
    skill_match: float | None = None
    experience: float | None = None
    education: float | None = None
    final: float | None = None


class RankingResult(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    company_id: uuid.UUID
    score_breakdown: ScoreBreakdown
    matched_skills: list[Any] | None = None
    missing_skills: list[Any] | None = None
    truly_missing_skills: list[Any] | None = None
    likely_covered_skills: list[dict[str, Any]] | None = None
    ranking_mode_used: str | None = None
    top_matching_chunks: list[Any] | None = None
    passed_hard_filter: bool
    rank_position: int | None = None
    ranked_at: datetime


class SkillMapStatus(BaseModel):
    job_id: str
    ranking_mode: str
    status: str
    built_at: datetime | None = None
    error: str | None = None
    skill_count: int | None = None
    implied_skills_total: int | None = None


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    department: str | None
    created_at: datetime
    updated_at: datetime
    resume_count: int = 0
    indexed_count: int = 0
    top_score: float | None = None
    pipeline_stage: str = "uploaded"
    last_ranked_at: datetime | None = None
    ranking_mode: str = "keyword"
    skill_map_status: str = "pending"


class DashboardCompany(BaseModel):
    id: uuid.UUID
    name: str
    settings: dict[str, Any]


class DashboardSummary(BaseModel):
    total_jobs: int
    open_jobs: int
    total_candidates: int
    indexed_candidates: int
    ranked_candidates: int


class DashboardResponse(BaseModel):
    company: DashboardCompany
    summary: DashboardSummary
    jobs: list[JobSummary]
