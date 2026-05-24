"""Embedding-based skill normalization against a growing canonical taxonomy."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.model_cache import ModelCache

logger = logging.getLogger(__name__)

TAXONOMY_PATH = Path("storage/skill_taxonomy.json")
SIMILARITY_THRESHOLD = 0.85


class SkillNormalizer:
    """Map raw skill strings to canonical skills via MiniLM cosine similarity."""

    def __init__(self, taxonomy_path: Path | None = None) -> None:
        self._taxonomy_path = taxonomy_path or TAXONOMY_PATH
        self._canonical_skills: List[str] = self._load_taxonomy()
        self._canonical_embeddings: np.ndarray | None = None

    def _load_taxonomy(self) -> List[str]:
        if not self._taxonomy_path.exists():
            self._taxonomy_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_taxonomy(skills=[])
            return []
        with open(self._taxonomy_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(skill) for skill in data]
        if isinstance(data, dict):
            skills = data.get("skills", data.get("canonical_skills", []))
            return [str(skill) for skill in skills]
        return []

    def _ensure_embeddings(self) -> None:
        if self._canonical_embeddings is not None:
            return
        if not self._canonical_skills:
            self._canonical_embeddings = np.empty((0, 384))
            return
        model = ModelCache.get_instance().get_minilm()
        self._canonical_embeddings = model.encode(
            self._canonical_skills,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def _invalidate_embeddings(self) -> None:
        self._canonical_embeddings = None

    def save_taxonomy(self, skills: List[str] | None = None) -> None:
        skills_to_save = self._canonical_skills if skills is None else skills
        self._taxonomy_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._taxonomy_path, "w", encoding="utf-8") as f:
            json.dump(skills_to_save, f, indent=2)

    def normalize(self, raw_skills: List[str]) -> List[str]:
        """Return deduplicated canonical skill strings for raw inputs."""
        if not raw_skills:
            return []

        model = ModelCache.get_instance().get_minilm()
        result: List[str] = []
        seen: set[str] = set()
        taxonomy_updated = False

        for raw in raw_skills:
            skill = raw.lower().strip()
            if not skill:
                continue

            canonical = self._map_skill(skill, model)
            if canonical not in self._canonical_skills:
                self._add_canonical(canonical, model)
                taxonomy_updated = True

            if canonical not in seen:
                seen.add(canonical)
                result.append(canonical)

        if taxonomy_updated:
            self.save_taxonomy()

        return result

    def _add_canonical(self, skill: str, model) -> None:
        embedding = model.encode([skill], convert_to_numpy=True, show_progress_bar=False)
        self._canonical_skills.append(skill)
        if self._canonical_embeddings is None or self._canonical_embeddings.size == 0:
            self._canonical_embeddings = embedding
        else:
            self._canonical_embeddings = np.vstack([self._canonical_embeddings, embedding])

    def _map_skill(self, skill: str, model) -> str:
        if not self._canonical_skills:
            return skill

        self._ensure_embeddings()
        embedding = model.encode([skill], convert_to_numpy=True, show_progress_bar=False)
        similarities = cosine_similarity(embedding, self._canonical_embeddings)[0]
        best_idx = int(np.argmax(similarities))
        if float(similarities[best_idx]) > SIMILARITY_THRESHOLD:
            return self._canonical_skills[best_idx]
        return skill
