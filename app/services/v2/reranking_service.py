"""Fast in-memory reranking from stored score components (no DB write)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Ranking

WEIGHT_KEYS = frozenset({"semantic", "skill_match", "experience", "education"})


def _validate_weights(weights: dict[str, float]) -> None:
    missing = WEIGHT_KEYS - set(weights.keys())
    if missing:
        raise ValueError(f"Missing weight keys: {sorted(missing)}")
    total = sum(float(weights[key]) for key in WEIGHT_KEYS)
    if not 0.99 <= total <= 1.01:
        raise ValueError("Weights must sum to between 0.99 and 1.01")


def rerank(job_id: str, new_weights: dict[str, float], db: Session) -> list[dict[str, Any]]:
    _validate_weights(new_weights)

    job_uuid = uuid.UUID(job_id)
    rankings = db.execute(select(Ranking).where(Ranking.job_id == job_uuid)).scalars().all()
    if not rankings:
        return []

    results: list[dict[str, Any]] = []
    for ranking in rankings:
        if not ranking.passed_hard_filter:
            new_final = 0.0
        else:
            new_final = (
                new_weights["semantic"] * (ranking.semantic_score or 0.0)
                + new_weights["skill_match"] * (ranking.skill_score or 0.0)
                + new_weights["experience"] * (ranking.experience_score or 0.0)
                + new_weights["education"] * (ranking.education_score or 0.0)
            )
        results.append(
            {
                "candidate_id": str(ranking.candidate_id),
                "final_score": round(new_final, 4),
                "score_breakdown": {
                    "semantic": ranking.semantic_score,
                    "skill_match": ranking.skill_score,
                    "experience": ranking.experience_score,
                    "education": ranking.education_score,
                },
                "matched_skills": ranking.matched_skills or [],
                "missing_skills": ranking.missing_skills or [],
                "rank_position": 0,
            }
        )

    results.sort(key=lambda row: row["final_score"], reverse=True)
    for position, row in enumerate(results, start=1):
        row["rank_position"] = position

    return results
