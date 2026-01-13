"""RAG service for index building and query processing."""
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, UTC, timedelta
import numpy as np
from app.core.config import COLLECTIONS_ROOT
from app.utils.paths import get_collection_root, assert_collection_exists
from app.utils.embeddings import generate_embeddings
from app.utils.faiss_index import (
    build_index, load_index, load_resume_mapping,
    get_index_metadata
)
from app.utils.rag_retrieval import retrieve_candidates
from app.utils.rag_prompts import build_system_prompt, build_user_prompt
from app.services.llm_service import stream_llm_response, get_available_providers

logger = logging.getLogger(__name__)


def get_rag_base_path(company_id: str, collection_id: str) -> Path:
    """Get RAG base directory path."""
    collection_root = get_collection_root(company_id, collection_id)
    return collection_root / "rag"


def is_phase2_complete(collection_root: Path) -> bool:
    """Check if Phase 2 processing is complete."""
    meta_file = collection_root / "collection_meta.json"
    if not meta_file.exists():
        return False
    
    try:
        meta = json.loads(meta_file.read_text())
        return meta.get("processing_status") == "completed"
    except Exception:
        return False


def is_index_built(rag_base: Path) -> bool:
    """Check if FAISS index exists."""
    index_path = rag_base / "index" / "faiss_index.index"
    return index_path.exists()


def build_rag_index(company_id: str, collection_id: str) -> dict:
    """
    Build RAG index from processed resumes.
    
    Args:
        company_id: Company identifier
        collection_id: Collection identifier
        
    Returns:
        Build summary dictionary
    """
    collection_root = get_collection_root(company_id, collection_id)
    assert_collection_exists(collection_root)
    
    # Check Phase 2 completion
    if not is_phase2_complete(collection_root):
        raise ValueError("Phase 2 processing must be completed before building RAG index")
    
    processed_dir = collection_root / "processed"
    resume_files = sorted(processed_dir.glob("*.txt"))
    
    if not resume_files:
        raise ValueError("No processed resumes found")
    
    # Prepare texts and mapping
    resume_texts = []
    resume_mapping = {}
    
    for idx, resume_file in enumerate(resume_files):
        text = resume_file.read_text(encoding='utf-8', errors='ignore')
        resume_texts.append(text)
        resume_mapping[idx] = resume_file.name
    
    # Generate embeddings
    logger.info(f"Generating embeddings for {len(resume_texts)} resumes")
    embeddings = generate_embeddings(resume_texts)
    
    # Setup RAG directories
    rag_base = get_rag_base_path(company_id, collection_id)
    index_dir = rag_base / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    
    index_path = index_dir / "faiss_index.index"
    mapping_path = index_dir / "resume_mapping.json"
    meta_path = index_dir / "index_meta.json"
    embeddings_backup = index_dir / "embeddings.npy"
    
    # Build and save index
    build_index(embeddings, resume_mapping, index_path, mapping_path, meta_path)
    
    # Save embeddings backup
    np.save(embeddings_backup, embeddings)
    
    logger.info(f"RAG index built successfully for {collection_id}")
    
    return {
        "status": "completed",
        "num_vectors": len(resume_texts),
        "dimension": embeddings.shape[1],
        "index_path": str(index_path.relative_to(collection_root))
    }


def get_rag_status(company_id: str, collection_id: str) -> dict:
    """Get RAG status for a collection."""
    try:
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        phase2_complete = is_phase2_complete(collection_root)
        rag_base = get_rag_base_path(company_id, collection_id)
        index_built = is_index_built(rag_base)
        
        # Check Phase 3 availability
        ranking_path = collection_root / "outputs" / "ranking_results.json"
        has_ranking = ranking_path.exists()
        
        features_enabled = {
            "phase2_complete": phase2_complete,
            "phase3_available": has_ranking,
            "llm_providers": get_available_providers()
        }
        
        index_stats = None
        if index_built:
            meta_path = rag_base / "index" / "index_meta.json"
            index_stats = get_index_metadata(meta_path)
        
        return {
            "rag_available": phase2_complete,
            "features_enabled": features_enabled,
            "index_built": index_built,
            "index_stats": index_stats
        }
    except Exception as e:
        logger.error(f"Error getting RAG status: {e}")
        return {
            "rag_available": False,
            "features_enabled": {},
            "index_built": False,
            "index_stats": None
        }


def hash_query(query: str) -> str:
    """Hash query for cache key."""
    return hashlib.sha256(query.encode('utf-8')).hexdigest()


def get_cached_response(cache_path: Path, query_hash: str) -> Optional[str]:
    """Get cached response if valid."""
    cache_file = cache_path / f"{query_hash}.json"
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check TTL (1 hour)
        cached_at = datetime.fromisoformat(cache_data.get("cached_at", ""))
        if datetime.now(UTC) - cached_at > timedelta(hours=1):
            cache_file.unlink()  # Delete expired cache
            return None
        
        return cache_data.get("response", "")
    except Exception:
        return None


def save_cached_response(cache_path: Path, query_hash: str, response: str) -> None:
    """Save response to cache."""
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_file = cache_path / f"{query_hash}.json"
    
    cache_data = {
        "query_hash": query_hash,
        "cached_at": datetime.now(UTC).isoformat(),
        "response": response
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)


async def process_rag_query(
    company_id: str,
    collection_id: str,
    query: str,
    top_k: int = 5,
    filters: Optional[dict] = None,
    include_context: bool = True,
    use_ranking: bool = True
) -> AsyncGenerator[str, None]:
    """
    Process RAG query and stream LLM response.
    
    Args:
        company_id: Company identifier
        collection_id: Collection identifier
        query: User query
        top_k: Number of candidates to retrieve
        filters: Filter options
        include_context: Whether to include context in prompt
        use_ranking: Whether to use Phase 3 ranking
        
    Yields:
        Chunks of LLM response
    """
    try:
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        # Check Phase 2
        if not is_phase2_complete(collection_root):
            yield "Error: Phase 2 processing must be completed before using RAG"
            return
        
        # Lazy index building
        rag_base = get_rag_base_path(company_id, collection_id)
        if not is_index_built(rag_base):
            logger.info(f"Index not found, building for {collection_id}")
            build_rag_index(company_id, collection_id)
        
        # Check cache
        cache_path = rag_base / "cache"
        query_hash = hash_query(query)
        cached = get_cached_response(cache_path, query_hash)
        if cached:
            logger.info(f"Using cached response for query hash: {query_hash[:8]}")
            yield cached
            return
        
        # Load index and mapping
        index_path = rag_base / "index" / "faiss_index.index"
        mapping_path = rag_base / "index" / "resume_mapping.json"
        
        index = load_index(index_path)
        resume_mapping = load_resume_mapping(mapping_path)
        
        # Generate query embedding
        from app.utils.embeddings import generate_query_embedding
        query_embedding = generate_query_embedding(query)
        
        # Retrieve candidates
        candidates = retrieve_candidates(
            index=index,
            query=query,
            query_embedding=query_embedding,
            resume_mapping=resume_mapping,
            collection_root=collection_root,
            top_k=top_k,
            filters=filters,
            use_ranking=use_ranking
        )
        
        if not candidates:
            yield "No candidates found matching the query and filters."
            return
        
        # Check Phase 3 availability for prompt
        ranking_path = collection_root / "outputs" / "ranking_results.json"
        has_ranking = ranking_path.exists() and use_ranking
        
        # Build prompts
        system_prompt = build_system_prompt(has_ranking=has_ranking)
        user_prompt = build_user_prompt(query, candidates, include_context)
        
        # Get LLM provider (prefer OpenAI, fallback to Anthropic)
        providers = get_available_providers()
        provider = providers[0] if providers else "openai"
        
        # Stream LLM response
        full_response = ""
        async for chunk in stream_llm_response(system_prompt, user_prompt, provider):
            full_response += chunk
            yield chunk
        
        # Cache response
        if full_response and not full_response.startswith("Error:"):
            save_cached_response(cache_path, query_hash, full_response)
        
    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        yield f"Error: {str(e)}"
