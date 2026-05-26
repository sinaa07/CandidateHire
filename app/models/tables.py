"""SQLAlchemy ORM models for multi-tenant metadata (SQLite)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _default_ranking_config() -> dict[str, Any]:
    return {
        "weights": {
            "semantic": 0.45,
            "skill_match": 0.30,
            "experience": 0.15,
            "education": 0.10,
        },
        "hard_filters": {
            "min_skill_overlap": 0.0,
            "min_experience_years": 0,
        },
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=lambda: {})

    jobs: Mapped[list["Job"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    users: Mapped[list["User"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    company: Mapped["Company"] = relationship(back_populates="users")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ranking_config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=_default_ranking_config,
    )
    ranking_mode: Mapped[str] = mapped_column(String(32), default="keyword", nullable=False)
    skill_implied_by_map_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    skill_map_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    skill_map_built_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    skill_map_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )

    company: Mapped["Company"] = relationship(back_populates="jobs")
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    rankings: Mapped[list["Ranking"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    processed_text_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["Job"] = relationship(back_populates="candidates")
    index_row: Mapped["CandidateIndex | None"] = relationship(
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
    )
    rankings: Mapped[list["Ranking"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class CandidateIndex(Base):
    __tablename__ = "candidate_indices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    extracted_skills: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    normalized_skills: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    job_titles: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    organizations: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    experience_entries: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    total_experience_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    most_recent_role_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    education_entries: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    education_tier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_texts: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    chunk_embeddings_path: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="index_row")


class Ranking(Base):
    __tablename__ = "rankings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_matching_chunks: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    matched_skills: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    missing_skills: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    truly_missing_skills: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    likely_covered_skills: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    ranking_mode_used: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed_hard_filter: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scoring_config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ranked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["Job"] = relationship(back_populates="rankings")
    candidate: Mapped["Candidate"] = relationship(back_populates="rankings")
