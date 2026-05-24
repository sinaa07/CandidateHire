"""Structured intelligence extraction from resume plain text."""
from __future__ import annotations

import logging
from typing import Dict, Optional

from app.utils.experience import compute_experience_signals
from app.utils.latency_tracker import LatencyRecorder, STAGE_NER, STAGE_PARSING
from app.utils.ner.base import ExtractedEntities
from app.utils.ner.normalizer import normalize_entities
from app.utils.ner.rules import extract_rule_based_entities
from app.utils.ner.spacy_ner import extract_spacy_entities
from app.utils.section_parser import parse_sections, sections_to_dict

logger = logging.getLogger(__name__)


def extract_resume_intelligence(
    text: str,
    filename: str,
    recorder: Optional[LatencyRecorder] = None,
) -> Dict:
    """
    Parse sections, extract entities, and compute experience signals.

    Args:
        text: Resume plain text.
        filename: Source filename for logging.
        recorder: Optional latency recorder.

    Returns:
        Dict with ``sections``, ``entities``, and ``experience`` keys.
    """
    try:
        if recorder:
            with recorder.stage(STAGE_PARSING):
                sections, boundaries = parse_sections(text, return_boundaries=True)
        else:
            sections, boundaries = parse_sections(text, return_boundaries=True)
        sections_dict = sections_to_dict(sections, boundaries=boundaries)

        if recorder:
            with recorder.stage(STAGE_NER):
                rule_entities = extract_rule_based_entities(text)
                spacy_entities = extract_spacy_entities(text)
        else:
            rule_entities = extract_rule_based_entities(text)
            spacy_entities = extract_spacy_entities(text)

        entities_dict = rule_entities.to_dict()
        entities_dict["organizations"].extend(spacy_entities["organizations"])
        entities_dict["roles"].extend(spacy_entities["roles"])
        entities_dict["locations"].extend(spacy_entities["locations"])

        entities_dict["organizations"] = sorted(list(set(entities_dict["organizations"])))
        entities_dict["roles"] = sorted(list(set(entities_dict["roles"])))
        entities_dict["locations"] = sorted(list(set(entities_dict["locations"])))

        entities_dict = normalize_entities(entities_dict)
        normalized_entities = ExtractedEntities.from_dict(entities_dict)
        experience_signals = compute_experience_signals(normalized_entities)

        return {
            "sections": sections_dict,
            "entities": entities_dict,
            "experience": experience_signals,
        }
    except Exception as exc:
        logger.warning("Failed to extract intelligence from %s: %s", filename, exc)
        return {
            "sections": {
                "summary": "",
                "experience": "",
                "skills": "",
                "education": "",
                "projects": "",
                "other": "",
            },
            "entities": {
                "skills": {},
                "roles": [],
                "organizations": [],
                "education": {},
                "experience": {},
                "locations": [],
            },
            "experience": {
                "experience_depth": 0.0,
                "stability": 0.0,
                "years_min": None,
                "years_max": None,
                "role_count": 0,
                "earliest_date": None,
                "latest_date": None,
            },
        }
