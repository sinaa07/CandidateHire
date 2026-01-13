"""Utility for managing FAISS vector index."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import faiss

logger = logging.getLogger(__name__)


def create_faiss_index(dimension: int = 384) -> faiss.Index:
    """
    Create a new FAISS index.
    
    Args:
        dimension: Embedding dimension (default 384 for all-MiniLM-L6-v2)
        
    Returns:
        FAISS IndexFlatL2 instance
    """
    # IndexFlatL2 uses L2 distance; normalize for cosine similarity
    index = faiss.IndexFlatL2(dimension)
    # TODO: For GPU support, use faiss.IndexFlatL2 with GPU resources
    return index


def build_index(
    embeddings: np.ndarray,
    resume_mapping: Dict[int, str],
    index_path: Path,
    mapping_path: Path,
    meta_path: Path
) -> None:
    """
    Build and save FAISS index with metadata.
    
    Args:
        embeddings: numpy array of shape (n_vectors, dimension)
        resume_mapping: Dictionary mapping vector_id -> filename
        index_path: Path to save FAISS index
        mapping_path: Path to save resume mapping JSON
        meta_path: Path to save index metadata JSON
    """
    # Normalize embeddings for cosine similarity with L2 distance
    faiss.normalize_L2(embeddings)
    
    # Create and populate index
    index = create_faiss_index(embeddings.shape[1])
    index.add(embeddings.astype('float32'))
    
    # Save index
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    
    # Save resume mapping
    with open(mapping_path, 'w') as f:
        json.dump(resume_mapping, f, indent=2)
    
    # Save metadata
    from datetime import datetime, UTC
    metadata = {
        "dimension": embeddings.shape[1],
        "num_vectors": embeddings.shape[0],
        "build_timestamp": datetime.now(UTC).isoformat(),
        "index_type": "IndexFlatL2"
    }
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Built FAISS index with {embeddings.shape[0]} vectors")


def load_index(index_path: Path) -> faiss.Index:
    """
    Load FAISS index from disk.
    
    Args:
        index_path: Path to FAISS index file
        
    Returns:
        Loaded FAISS index
    """
    if not index_path.exists():
        raise ValueError(f"Index file not found: {index_path}")
    return faiss.read_index(str(index_path))


def load_resume_mapping(mapping_path: Path) -> Dict[int, str]:
    """
    Load resume mapping from JSON.
    
    Args:
        mapping_path: Path to mapping JSON file
        
    Returns:
        Dictionary mapping vector_id -> filename
    """
    if not mapping_path.exists():
        raise ValueError(f"Mapping file not found: {mapping_path}")
    with open(mapping_path, 'r') as f:
        mapping = json.load(f)
    # Convert string keys to int (JSON keys are strings)
    return {int(k): v for k, v in mapping.items()}


def search_index(
    index: faiss.Index,
    query_embedding: np.ndarray,
    k: int = 50
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Search FAISS index for top-k similar vectors.
    
    Args:
        index: FAISS index
        query_embedding: Query embedding vector (1D array)
        k: Number of results to return
        
    Returns:
        Tuple of (distances, indices) arrays
    """
    # Normalize query embedding
    query_normalized = query_embedding.copy().reshape(1, -1).astype('float32')
    faiss.normalize_L2(query_normalized)
    
    # Search
    distances, indices = index.search(query_normalized, min(k, index.ntotal))
    return distances[0], indices[0]


def get_index_metadata(meta_path: Path) -> dict:
    """
    Load index metadata.
    
    Args:
        meta_path: Path to metadata JSON
        
    Returns:
        Metadata dictionary
    """
    if not meta_path.exists():
        return {}
    with open(meta_path, 'r') as f:
        return json.load(f)
