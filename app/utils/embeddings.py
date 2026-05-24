"""Utility for generating embeddings using sentence-transformers."""
import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from app.utils.latency_tracker import LatencyRecorder, STAGE_EMBEDDING_GENERATION

logger = logging.getLogger(__name__)

# Global model instance (lazy-loaded)
_model: SentenceTransformer | None = None
_model_name = "all-MiniLM-L6-v2"
_embedding_dim = 384


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize the embedding model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {_model_name}")
        _model = SentenceTransformer(_model_name)
        logger.info("Embedding model loaded successfully")
    return _model


def generate_embeddings(
    texts: List[str],
    recorder: Optional[LatencyRecorder] = None,
) -> np.ndarray:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of text strings
        recorder: Optional latency recorder
        
    Returns:
        numpy array of shape (n_texts, 384)
    """
    model = get_embedding_model()
    if recorder:
        with recorder.stage(STAGE_EMBEDDING_GENERATION):
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    else:
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings


def generate_query_embedding(
    query: str,
    recorder: Optional[LatencyRecorder] = None,
) -> np.ndarray:
    """
    Generate embedding for a single query.
    
    Args:
        query: Query text
        recorder: Optional latency recorder
        
    Returns:
        numpy array of shape (384,)
    """
    model = get_embedding_model()
    if recorder:
        with recorder.stage(STAGE_EMBEDDING_GENERATION):
            embedding = model.encode([query], convert_to_numpy=True)[0]
    else:
        embedding = model.encode([query], convert_to_numpy=True)[0]
    return embedding
