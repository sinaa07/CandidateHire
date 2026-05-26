"""LLM-powered implied-by skill map for contextual ranking."""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.tables import Job
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def _clean_llm_json_response(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start : end + 1]
    return text


def _normalize_skill_map(skill_map: dict[Any, Any]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, vals in skill_map.items():
        if not isinstance(vals, list):
            continue
        k = str(key).lower().strip()
        if not k:
            continue
        normalized[k] = [str(v).lower().strip() for v in vals if str(v).strip()]
    return normalized


def _save_build_artifacts(
    base_path: str,
    *,
    normalized_map: dict[str, list[str]],
    raw_response: str,
    model_name: str,
    jd_word_count: int,
) -> None:
    os.makedirs(base_path, exist_ok=True)

    map_path = os.path.join(base_path, "implied_by_map.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(normalized_map, f, indent=2)

    raw_path = os.path.join(base_path, "raw_llm_response.txt")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_response)

    meta = {
        "built_at": datetime.utcnow().isoformat(),
        "model_used": model_name,
        "jd_word_count": jd_word_count,
        "skill_count": len(normalized_map),
        "implied_skills_total": sum(len(v) for v in normalized_map.values()),
    }
    meta_path = os.path.join(base_path, "build_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


async def build_skill_implied_by_map(
    job_id: str,
    company_id: str,
    db: Session,
) -> dict:
    job_uuid = uuid.UUID(job_id)
    job = db.query(Job).filter_by(id=job_uuid).first()
    if not job or not job.jd_text:
        raise ValueError("Job not found or has no JD text")

    job.skill_map_status = "building"
    db.commit()

    prompt = """You are a skill taxonomy expert for a hiring platform \
that handles ALL types of roles — technology, marketing, finance, \
healthcare, legal, operations, design, sales, and more.

Given the job description below, do two things:

1. Extract ALL required skills (explicit and strongly implied)
2. For each skill, generate a comprehensive list of specific tools,
   technologies, sub-skills, frameworks, methodologies, certifications,
   or alternate names that a candidate might write on their resume
   that would strongly imply they have that skill.

Think of it as: "if candidate writes X, they satisfy requirement Y"

Job Description:
{jd_text}

Rules:
- Cover ALL domains in the JD, not just technical skills
- Include the canonical skill itself in its own implied list
  so exact string matches always work
- Include common abbreviations and alternate spellings
- Include specific tools that are subsets of a category skill
- Include related certifications where relevant
- A candidate skill implies a JD skill only if the relationship
  is strong and realistic, not superficial
- Keep each implied list focused: 10-20 items maximum
- Lowercase all skills in output
- Return JSON only, no explanation, no markdown backticks

Return format:
{{
  "skill_implied_by_map": {{
    "jd_skill": ["implied_skill_1", "implied_skill_2", ...]
  }}
}}""".format(jd_text=job.jd_text)

    base_path = f"storage/companies/{company_id}/jobs/{job_id}/skill_maps"
    model_name = ""
    raw_response = ""

    try:
        raw_response, model_name = await LLMService.complete(
            prompt,
            max_tokens=2000,
            temperature=0.1,
        )
    except Exception as exc:
        logger.exception("LLM call failed for job %s", job_id)
        job.skill_map_status = "failed"
        job.skill_map_error = str(exc)
        db.commit()
        return {}

    try:
        cleaned = _clean_llm_json_response(raw_response)
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        os.makedirs(base_path, exist_ok=True)
        raw_path = os.path.join(base_path, "raw_llm_response.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_response)
        job.skill_map_status = "failed"
        job.skill_map_error = "JSON parse failed"
        db.commit()
        return {}

    skill_map = result.get("skill_implied_by_map", {})
    if not isinstance(skill_map, dict):
        skill_map = {}

    normalized_map = _normalize_skill_map(skill_map)

    _save_build_artifacts(
        base_path,
        normalized_map=normalized_map,
        raw_response=raw_response,
        model_name=model_name,
        jd_word_count=len(job.jd_text.split()),
    )

    job.skill_implied_by_map_path = f"{base_path}/implied_by_map.json"
    job.skill_map_status = "ready"
    job.skill_map_built_at = datetime.utcnow()
    job.skill_map_error = None
    db.commit()

    return normalized_map


def load_skill_implied_by_map(job: Job) -> dict:
    if job.skill_map_status != "ready":
        return {}
    if not job.skill_implied_by_map_path:
        return {}
    if not os.path.exists(job.skill_implied_by_map_path):
        return {}

    try:
        with open(job.skill_implied_by_map_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception as exc:
        logger.warning(
            "Failed to load skill map for job %s: %s",
            job.id,
            exc,
        )
        return {}


def apply_implied_by_map(
    missing_skills: list[str],
    matched_skills: list[str],
    candidate_all_skills: list[str],
    implied_by_map: dict,
) -> tuple[list[str], list[dict]]:
    _ = matched_skills

    candidate_skills_lower = {s.lower().strip() for s in candidate_all_skills}

    truly_missing: list[str] = []
    likely_covered: list[dict] = []

    for jd_skill in missing_skills:
        jd_skill_lower = jd_skill.lower().strip()
        implied_by = set(implied_by_map.get(jd_skill_lower, []))
        covering = candidate_skills_lower & implied_by

        if covering:
            likely_covered.append(
                {
                    "skill": jd_skill,
                    "covered_by": sorted(covering),
                }
            )
        else:
            truly_missing.append(jd_skill)

    return truly_missing, likely_covered


def run_build_skill_implied_by_map_task(job_id: str, company_id: str) -> None:
    """Background wrapper: own DB session per skill-map build."""
    import asyncio
    from pathlib import Path

    from dotenv import load_dotenv

    from app.db.session import SessionLocal

    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    db = SessionLocal()
    try:
        asyncio.run(build_skill_implied_by_map(job_id, company_id, db))
    except Exception:
        logger.exception("Background skill map build failed for job %s", job_id)
    finally:
        db.close()
