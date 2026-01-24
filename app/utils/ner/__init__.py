"""NER (Named Entity Recognition) module for resume extraction."""

from app.utils.ner.base import ExtractedEntities
from app.utils.ner.rules import extract_rule_based_entities
from app.utils.ner.spacy_ner import extract_spacy_entities
from app.utils.ner.normalizer import normalize_entities

__all__ = [
    "ExtractedEntities",
    "extract_rule_based_entities",
    "extract_spacy_entities",
    "normalize_entities"
]
