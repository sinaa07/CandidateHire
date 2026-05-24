"""Singleton cache for MiniLM and NER models loaded once at first use."""
from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MINILM_NAME = "all-MiniLM-L6-v2"
_NER_MODEL = "dslim/bert-base-NER"


class ModelCache:
    """Thread-safe singleton holding MiniLM and Hugging Face NER pipeline."""

    _instance: ModelCache | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._minilm: SentenceTransformer | None = None
        self._ner_pipeline: Any | None = None

    @classmethod
    def get_instance(cls) -> ModelCache:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance._load_models()
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_models_health(cls) -> dict[str, str]:
        """Return load status without triggering model initialization."""
        if cls._instance is None:
            return {"minilm": "not_loaded", "ner": "not_loaded"}
        return {
            "minilm": "loaded" if cls._instance._minilm is not None else "not_loaded",
            "ner": "loaded" if cls._instance._ner_pipeline is not None else "not_loaded",
        }

    def _load_models(self) -> None:
        from sentence_transformers import SentenceTransformer
        from transformers import pipeline

        start = time.perf_counter()
        logger.info("Loading MiniLM model: %s", _MINILM_NAME)
        self._minilm = SentenceTransformer(_MINILM_NAME)
        logger.info("MiniLM loaded in %.2fs", time.perf_counter() - start)

        start = time.perf_counter()
        logger.info("Loading NER pipeline: %s", _NER_MODEL)
        self._ner_pipeline = pipeline(
            "ner",
            model=_NER_MODEL,
            aggregation_strategy="simple",
        )
        logger.info("NER pipeline loaded in %.2fs", time.perf_counter() - start)

    def get_minilm(self) -> SentenceTransformer:
        if self._minilm is None:
            raise RuntimeError("MiniLM model is not loaded")
        return self._minilm

    def get_ner_pipeline(self) -> Any:
        if self._ner_pipeline is None:
            raise RuntimeError("NER pipeline is not loaded")
        return self._ner_pipeline
