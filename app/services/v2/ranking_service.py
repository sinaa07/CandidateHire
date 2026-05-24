"""Synchronous v2 job ranking (embedding math on pre-indexed candidates)."""
from __future__ import annotations

import copy
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.tables import CandidateIndex, Job, Ranking, _default_ranking_config
from app.services.v2.indexing_service import _run_ner_chunked
from app.utils.chunker import chunk_text
from app.utils.model_cache import ModelCache
from app.utils.skill_normalizer import SkillNormalizer
from app.utils.skills import SKILLS, extract_skills

logger = logging.getLogger(__name__)


def _extract_jd_skills(jd_text: str) -> set[str]:
    ner = ModelCache.get_instance().get_ner_pipeline()
    entities = _run_ner_chunked(jd_text, ner)
    misc_skills = [
        e["word"].strip().lower()
        for e in entities
        if e.get("entity_group") == "MISC" and e.get("word", "").strip()
    ]
    keyword_skills = extract_skills(jd_text, SKILLS)
    raw_skills = sorted({s for s in misc_skills + keyword_skills if s and len(s) > 1})
    normalizer = SkillNormalizer()
    return set(normalizer.normalize(raw_skills))


def _apply_config_override(
    config: dict[str, Any],
    config_override: dict[str, Any] | None,
) -> dict[str, Any]:
    if not config_override:
        return config
    merged = copy.deepcopy(config)
    if "weights" in config_override:
        merged["weights"] = {**merged.get("weights", {}), **config_override["weights"]}
    if "hard_filters" in config_override:
        merged["hard_filters"] = {
            **merged.get("hard_filters", {}),
            **config_override["hard_filters"],
        }
    return merged


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _score_candidate(
    idx_record: CandidateIndex,
    jd_embeddings: np.ndarray,
    jd_skills: set[str],
    weights: dict[str, float],
    hard_filters: dict[str, float],
) -> dict[str, Any] | None:
    emb_path = idx_record.chunk_embeddings_path
    if not emb_path or not os.path.exists(emb_path):
        logger.warning("Missing embeddings for candidate %s", idx_record.candidate_id)
        return None

    candidate_emb = np.load(emb_path)
    if candidate_emb.size == 0 or jd_embeddings.size == 0:
        return None

    sim_matrix = cosine_similarity(jd_embeddings, candidate_emb)
    per_chunk_max = sim_matrix.max(axis=0)
    top_n = min(3, len(per_chunk_max))
    semantic_score = float(np.sort(per_chunk_max)[-top_n:].mean())

    top_chunk_indices = np.argsort(per_chunk_max)[-3:][::-1]
    chunk_texts = idx_record.chunk_texts or []
    top_matching_chunks = [
        {
            "chunk_text": chunk_texts[i][:200],
            "cosine_score": float(per_chunk_max[i]),
            "chunk_idx": int(i),
        }
        for i in top_chunk_indices
        if i < len(chunk_texts)
    ]

    candidate_skills = set(idx_record.normalized_skills or [])
    intersection = candidate_skills & jd_skills
    union = candidate_skills | jd_skills
    skill_score = len(intersection) / len(union) if union else 0.0
    matched_skills = sorted(intersection)
    missing_skills = sorted(jd_skills - candidate_skills)

    years = float(idx_record.total_experience_years or 0)
    log_score = min(math.log1p(years) / math.log1p(15), 1.0)

    if idx_record.most_recent_role_date:
        role_date = idx_record.most_recent_role_date
        if role_date.tzinfo is None:
            role_date = role_date.replace(tzinfo=timezone.utc)
        days_gap = (_utc_now() - role_date).days
        recency = max(0.0, 1.0 - days_gap / 730)
    else:
        recency = 0.5

    experience_score = 0.7 * log_score + 0.3 * recency
    education_score = float(idx_record.education_tier or 0) / 4.0

    passed = (
        skill_score >= hard_filters.get("min_skill_overlap", 0.0)
        and years >= hard_filters.get("min_experience_years", 0)
    )

    if passed:
        final_score = (
            weights["semantic"] * semantic_score
            + weights["skill_match"] * skill_score
            + weights["experience"] * experience_score
            + weights["education"] * education_score
        )
    else:
        final_score = 0.0

    return {
        "candidate_id": str(idx_record.candidate_id),
        "semantic_score": round(semantic_score, 4),
        "skill_score": round(skill_score, 4),
        "experience_score": round(experience_score, 4),
        "education_score": round(education_score, 4),
        "final_score": round(final_score, 4),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "top_matching_chunks": top_matching_chunks,
        "total_experience_years": round(years, 1),
        "education_tier": idx_record.education_tier,
        "passed_hard_filter": passed,
    }


async def rank_job(
    job_id: str,
    company_id: str,
    config_override: dict | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    if db is None:
        raise ValueError("db session is required")

    job_uuid = uuid.UUID(job_id)
    company_uuid = uuid.UUID(company_id)

    job = db.execute(
        select(Job).where(Job.id == job_uuid, Job.company_id == company_uuid)
    ).scalar_one_or_none()
    if job is None:
        raise ValueError("Job not found")

    config = copy.deepcopy(job.ranking_config or _default_ranking_config())
    config = _apply_config_override(config, config_override)

    weights = config["weights"]
    hard_filters = config["hard_filters"]

    jd_text = (job.jd_text or "").strip()
    if not jd_text:
        raise ValueError("Job has no JD text")

    jd_chunks = chunk_text(jd_text, section_label="jd")
    if not jd_chunks:
        jd_chunks = [{"text": jd_text, "section": "jd", "chunk_idx": 0}]

    minilm = ModelCache.get_instance().get_minilm()
    jd_embeddings = minilm.encode(
        [c["text"] for c in jd_chunks],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    jd_embeddings = np.asarray(jd_embeddings)

    jd_skills = _extract_jd_skills(jd_text)

    index_records = db.execute(
        select(CandidateIndex).where(CandidateIndex.job_id == job_uuid)
    ).scalars().all()

    if not index_records:
        return {"error": "No indexed candidates found"}

    results: list[dict[str, Any]] = []
    for idx_record in index_records:
        scored = _score_candidate(idx_record, jd_embeddings, jd_skills, weights, hard_filters)
        if scored is not None:
            results.append(scored)

    if not results:
        return {"error": "No indexed candidates with valid embeddings found"}

    results.sort(key=lambda row: row["final_score"], reverse=True)
    for position, row in enumerate(results, start=1):
        row["rank_position"] = position

    ranked_at = _utc_now()
    db.execute(delete(Ranking).where(Ranking.job_id == job_uuid))

    for row in results:
        db.add(
            Ranking(
                job_id=job_uuid,
                candidate_id=uuid.UUID(row["candidate_id"]),
                company_id=company_uuid,
                semantic_score=row["semantic_score"],
                skill_score=row["skill_score"],
                experience_score=row["experience_score"],
                education_score=row["education_score"],
                final_score=row["final_score"],
                top_matching_chunks=row["top_matching_chunks"],
                matched_skills=row["matched_skills"],
                missing_skills=row["missing_skills"],
                rank_position=row["rank_position"],
                passed_hard_filter=row["passed_hard_filter"],
                scoring_config_snapshot=config,
                ranked_at=ranked_at,
            )
        )

    db.commit()

    return {
        "job_id": job_id,
        "ranked_count": len(results),
        "ranked_at": ranked_at.isoformat(),
        "top_candidate": results[0] if results else None,
        "config_used": config,
    }
