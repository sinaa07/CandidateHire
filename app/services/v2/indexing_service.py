"""Offline per-candidate indexing pipeline (v2)."""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.v2.helpers import job_storage_path
from app.models.tables import Candidate, CandidateIndex
from app.utils.chunker import chunk_resume
from app.utils.model_cache import ModelCache
from app.utils.skill_normalizer import SkillNormalizer
from app.utils.skills import SKILLS, extract_skills
from app.utils.text_extraction import extract_text

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 100
MAX_EXPERIENCE_YEARS = 40.0
NER_CHUNK_WORDS = 307  # ~400 tokens at 1.3 multiplier
NER_OVERLAP_WORDS = 38  # ~50 tokens

SECTION_PATTERNS: dict[str, str] = {
    "experience": r"(?i)(work experience|experience|employment history)",
    "education": r"(?i)(education|academic background|qualifications)",
    "skills": r"(?i)(skills|technical skills|core competencies|technologies)",
    "projects": r"(?i)(projects|personal projects|key projects|portfolio)",
    "summary": r"(?i)(summary|profile|objective|about me)",
}

JOB_TITLE_PATTERN = re.compile(
    r"(?i)\b(software engineer|backend engineer|frontend engineer|"
    r"full[\s-]?stack|data scientist|ml engineer|devops|product manager|"
    r"tech lead|engineering manager|senior|junior|intern|associate)\b"
)

DATE_RANGE_PATTERN = re.compile(
    r"(?i)"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
    r"january|february|march|april|june|july|august|september|october|november|december)?"
    r"\s*(\d{4})\s*[-–—to]+\s*"
    r"(present|current|now|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
    r"january|february|march|april|june|july|august|september|october|november|december)?\s*\d{4})"
)

MONTH_NAMES: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

EDUCATION_TIERS: dict[int, list[str]] = {
    4: ["phd", "ph.d", "doctorate", "doctor of"],
    3: ["master", "m.tech", "m.sc", "mba", "m.e", "ms ", "m.s"],
    2: [
        "bachelor",
        "b.tech",
        "b.e",
        "b.sc",
        "b.com",
        "be ",
        "btech",
        "undergraduate",
        "b.a",
        "b.s",
    ],
    1: ["diploma", "certificate", "associate"],
    0: [],
}


def _fail(db: Session, candidate: Candidate, step: str, error: str) -> None:
    candidate.status = "failed"
    candidate.parse_error = f"{step}: {error}"[:2000]
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist candidate failure state for %s", candidate.id)


async def index_candidate(candidate_id: str, db: Session) -> None:
    """Index a single candidate. Never raises; updates status on failure."""
    step = "load"
    candidate: Candidate | None = None
    try:
        cand_uuid = uuid.UUID(candidate_id)
        candidate = db.get(Candidate, cand_uuid)
        if candidate is None:
            logger.error("Candidate not found: %s", candidate_id)
            return

        candidate.status = "processing"
        candidate.parse_error = None
        db.commit()

        step = "text_extraction"
        file_path = Path(candidate.file_path)
        if not file_path.is_file():
            _fail(db, candidate, step, f"File not found: {candidate.file_path}")
            return

        try:
            text = extract_text(file_path)
        except Exception as exc:
            _fail(db, candidate, step, str(exc))
            return

        text = (text or "").strip()
        if len(text) < MIN_TEXT_CHARS:
            _fail(db, candidate, step, f"Extracted text too short ({len(text)} chars)")
            return

        job_root = Path(job_storage_path(candidate.company_id, candidate.job_id))
        processed_dir = job_root / "resumes" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed_path = processed_dir / f"{candidate.id}.txt"
        processed_path.write_text(text, encoding="utf-8")
        candidate.processed_text_path = str(processed_path)

        step = "duplicate_detection"
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = db.execute(
            select(Candidate).where(
                Candidate.job_id == candidate.job_id,
                Candidate.content_hash == content_hash,
                Candidate.id != candidate.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            candidate.status = "duplicate"
            candidate.content_hash = content_hash
            db.commit()
            return

        candidate.content_hash = content_hash

        step = "section_detection"
        sections = _detect_sections(text)

        step = "ner"
        ner_pipeline = ModelCache.get_instance().get_ner_pipeline()
        entities = _run_ner_chunked(text, ner_pipeline)
        misc_skills = [
            e["word"].strip().lower()
            for e in entities
            if e.get("entity_group") == "MISC" and e.get("word", "").strip()
        ]
        keyword_skills = extract_skills(text, SKILLS)
        raw_skills = sorted(
            {s for s in misc_skills + keyword_skills if s and len(s) > 1}
        )
        extracted_orgs = sorted(
            {
                e["word"].strip()
                for e in entities
                if e.get("entity_group") == "ORG" and e.get("word", "").strip()
            }
        )
        extracted_titles = _extract_job_titles(text)

        step = "skill_normalization"
        normalizer = SkillNormalizer()
        normalized_skills = normalizer.normalize(raw_skills)

        step = "experience_extraction"
        experience_text = _section_text(sections, "experience") or text
        experience_entries, total_years, most_recent = _extract_experience(experience_text)

        step = "education_extraction"
        education_text = _section_text(sections, "education") or text
        education_tier = _extract_education_tier(education_text)
        education_entries = _extract_education_entries(education_text, education_tier)

        step = "chunk_and_embed"
        chunks = chunk_resume(sections)
        if not chunks:
            chunks = chunk_resume([{"section": "general", "text": text}])

        minilm = ModelCache.get_instance().get_minilm()
        chunk_texts = [c["text"] for c in chunks]
        embeddings = minilm.encode(
            chunk_texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        embeddings_dir = job_root / "embeddings"
        embeddings_dir.mkdir(parents=True, exist_ok=True)
        embeddings_path = embeddings_dir / f"{candidate.id}.npy"
        np.save(embeddings_path, np.asarray(embeddings))

        step = "write_index"
        index_row = db.execute(
            select(CandidateIndex).where(CandidateIndex.candidate_id == candidate.id)
        ).scalar_one_or_none()
        if index_row is None:
            index_row = CandidateIndex(
                candidate_id=candidate.id,
                job_id=candidate.job_id,
                company_id=candidate.company_id,
            )
            db.add(index_row)

        index_row.extracted_skills = raw_skills
        index_row.normalized_skills = normalized_skills
        index_row.job_titles = extracted_titles
        index_row.organizations = extracted_orgs
        index_row.experience_entries = experience_entries
        index_row.total_experience_years = total_years
        index_row.most_recent_role_date = most_recent
        index_row.education_entries = education_entries
        index_row.education_tier = education_tier
        index_row.chunk_texts = chunk_texts
        index_row.chunk_embeddings_path = str(embeddings_path)
        index_row.indexed_at = datetime.now(timezone.utc)

        candidate.status = "processed"
        db.commit()
        logger.info("Indexed candidate %s", candidate.id)

    except Exception as exc:
        logger.exception("Indexing failed for candidate %s at step %s", candidate_id, step)
        if candidate is not None:
            _fail(db, candidate, step, str(exc))


def _detect_sections(text: str) -> list[dict[str, str]]:
    matches: list[tuple[int, int, str]] = []
    for section, pattern in SECTION_PATTERNS.items():
        for match in re.finditer(pattern, text):
            matches.append((match.start(), match.end(), section))

    if not matches:
        return [{"section": "general", "text": text.strip()}]

    matches.sort(key=lambda item: item[0])
    sections: list[dict[str, str]] = []
    if matches[0][0] > 0:
        lead = text[: matches[0][0]].strip()
        if lead:
            sections.append({"section": "general", "text": lead})

    for idx, (start, end, section) in enumerate(matches):
        next_start = matches[idx + 1][0] if idx + 1 < len(matches) else len(text)
        body = text[end:next_start].strip()
        if body:
            sections.append({"section": section, "text": body})

    return sections or [{"section": "general", "text": text.strip()}]


def _section_text(sections: list[dict[str, str]], name: str) -> str:
    for section in sections:
        if section.get("section") == name:
            return section.get("text", "")
    return ""


def _ner_word_chunks(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= NER_CHUNK_WORDS:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + NER_CHUNK_WORDS, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(0, end - NER_OVERLAP_WORDS)
    return chunks


def _run_ner_chunked(text: str, ner_pipeline: Any) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for chunk in _ner_word_chunks(text):
        try:
            results = ner_pipeline(chunk)
        except Exception as exc:
            logger.warning("NER chunk failed: %s", exc)
            continue
        if not results:
            continue
        for ent in results:
            if not isinstance(ent, dict):
                continue
            word = (ent.get("word") or "").strip()
            label = ent.get("entity_group") or ent.get("entity") or ""
            if not word:
                continue
            key = (word.lower(), label)
            if key in seen:
                continue
            seen.add(key)
            merged.append(ent)
    return merged


def _extract_job_titles(text: str) -> list[str]:
    return sorted({m.group(0).strip() for m in JOB_TITLE_PATTERN.finditer(text)})


def _parse_month_year(month_str: str | None, year_str: str) -> date | None:
    try:
        year = int(year_str)
    except ValueError:
        return None
    month = 1
    if month_str:
        month = MONTH_NAMES.get(month_str.lower().strip(), 1)
    return date(year, month, 1)


def _parse_end_token(token: str) -> date | None:
    token = token.strip().lower()
    if token in {"present", "current", "now"}:
        return date.today()
    month_match = re.match(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
        r"january|february|march|april|june|july|august|september|october|november|december)"
        r"\s*(\d{4})\s*$",
        token,
        re.IGNORECASE,
    )
    if month_match:
        return _parse_month_year(month_match.group(1), month_match.group(2))
    if re.fullmatch(r"\d{4}", token):
        return date(int(token), 12, 31)
    return None


def _months_between(start: date, end: date) -> int:
    if end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _extract_experience(
    experience_text: str,
) -> tuple[list[dict[str, Any]], float, datetime | None]:
    entries: list[dict[str, Any]] = []
    total_months = 0
    latest_end: date | None = None

    for match in DATE_RANGE_PATTERN.finditer(experience_text):
        start_month, start_year, end_token = match.groups()
        start_date = _parse_month_year(start_month, start_year)
        end_date = _parse_end_token(end_token)
        if start_date is None or end_date is None:
            continue

        duration = _months_between(start_date, end_date)
        total_months += duration
        if latest_end is None or end_date > latest_end:
            latest_end = end_date

        snippet_start = max(0, match.start() - 40)
        snippet_end = min(len(experience_text), match.end() + 40)
        entries.append(
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_months": duration,
                "raw_text_snippet": experience_text[snippet_start:snippet_end].strip(),
            }
        )

    total_years = min(total_months / 12.0, MAX_EXPERIENCE_YEARS)
    most_recent = (
        datetime(latest_end.year, latest_end.month, latest_end.day, tzinfo=timezone.utc)
        if latest_end
        else None
    )
    return entries, round(total_years, 2), most_recent


def _extract_education_tier(education_text: str) -> int:
    lowered = education_text.lower()
    for tier in sorted(EDUCATION_TIERS.keys(), reverse=True):
        for keyword in EDUCATION_TIERS[tier]:
            if keyword in lowered:
                return tier
    return 0


def _extract_education_entries(education_text: str, tier: int) -> list[dict[str, Any]]:
    if tier == 0:
        return []
    matched = []
    lowered = education_text.lower()
    for kw in EDUCATION_TIERS.get(tier, []):
        if kw in lowered:
            matched.append(kw.strip())
    return [{"tier": tier, "matched_keywords": sorted(set(matched))}]
