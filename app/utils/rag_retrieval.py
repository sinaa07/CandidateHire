"""Two-stage retrieval algorithm for RAG."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from app.utils.skills import extract_skills, skill_overlap_score, SKILLS
from app.utils.faiss_index import search_index, load_resume_mapping
from app.utils.embeddings import generate_query_embedding

logger = logging.getLogger(__name__)


def load_ranking_results(ranking_path: Path) -> Dict[str, dict]:
    """
    Load Phase 3 ranking results.
    
    Args:
        ranking_path: Path to ranking_results.json
        
    Returns:
        Dictionary mapping filename -> ranking data
    """
    if not ranking_path.exists():
        return {}
    
    with open(ranking_path, 'r') as f:
        results = json.load(f)
    
    # Build lookup dictionary
    ranking_dict = {}
    for result in results:
        filename = result.get("filename", "")
        ranking_dict[filename] = {
            "rank": result.get("rank", 999),
            "final_score": result.get("final_score", 0.0),
            "tfidf_score": result.get("tfidf_score", 0.0),
            "skill_score": result.get("skill_score", 0.0),
            "explainability": result.get("explainability", {})
        }
    
    return ranking_dict


def get_resume_text_excerpt(resume_path: Path, max_chars: int = 300) -> str:
    """
    Get excerpt from resume text.
    
    Args:
        resume_path: Path to processed resume .txt file
        max_chars: Maximum characters in excerpt
        
    Returns:
        Text excerpt
    """
    if not resume_path.exists():
        return ""
    
    try:
        text = resume_path.read_text(encoding='utf-8', errors='ignore')
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
    except Exception as e:
        logger.warning(f"Failed to read excerpt from {resume_path}: {e}")
        return ""


def retrieve_candidates(
    index,
    query: str,
    query_embedding: np.ndarray,
    resume_mapping: Dict[int, str],
    collection_root: Path,
    top_k: int = 5,
    filters: Optional[dict] = None,
    use_ranking: bool = True
) -> List[dict]:
    """
    Two-stage retrieval: FAISS search + re-ranking.
    
    Args:
        index: FAISS index
        query: Query text
        query_embedding: Query embedding vector
        resume_mapping: Vector ID -> filename mapping
        collection_root: Collection root path
        top_k: Final number of candidates to return
        filters: Filter options
        use_ranking: Whether to use Phase 3 ranking
        
    Returns:
        List of candidate dictionaries with scores and metadata
    """
    filters = filters or {}
    
    # Stage 1: FAISS semantic search (top 50)
    distances, indices = search_index(index, query_embedding, k=50)
    
    # Convert distances to similarities (1 / (1 + distance))
    similarities = 1.0 / (1.0 + distances)
    
    # Load Phase 3 ranking if available
    ranking_path = collection_root / "outputs" / "ranking_results.json"
    ranking_dict = load_ranking_results(ranking_path) if use_ranking else {}
    has_ranking = len(ranking_dict) > 0
    
    # Load processed resumes for skill extraction
    processed_dir = collection_root / "processed"
    
    # Extract query skills
    query_skills = set(extract_skills(query, SKILLS))
    
    candidates = []
    
    for idx, (distance, vector_id) in enumerate(zip(distances, indices)):
        if vector_id not in resume_mapping:
            continue
        
        filename = resume_mapping[vector_id]
        faiss_similarity = similarities[idx]
        
        # Get ranking data if available
        ranking_data = ranking_dict.get(filename, {})
        ranking_score = ranking_data.get("final_score", 0.0) if has_ranking else 0.0
        rank_position = ranking_data.get("rank", 999) if has_ranking else 999
        
        # Extract skills from resume
        resume_path = processed_dir / filename
        resume_text = resume_path.read_text(encoding='utf-8', errors='ignore') if resume_path.exists() else ""
        resume_skills = set(extract_skills(resume_text, SKILLS))
        skill_score = skill_overlap_score(query_skills, resume_skills) if query_skills else 0.0
        
        # Combine scores
        if has_ranking:
            # 0.4 × FAISS + 0.3 × Phase3 + 0.3 × skills
            combined_score = 0.4 * faiss_similarity + 0.3 * ranking_score + 0.3 * skill_score
        else:
            # 0.6 × FAISS + 0.4 × skills
            combined_score = 0.6 * faiss_similarity + 0.4 * skill_score
        
        # Apply filters (rank_position: lower is better, e.g., 1 is best)
        if filters.get("min_rank_position") is not None:
            # min_rank_position means "at least this good" (rank <= min)
            if rank_position > filters["min_rank_position"]:
                continue
        
        if filters.get("max_rank_position") is not None:
            # max_rank_position means "at most this good" (rank >= max)
            if rank_position < filters["max_rank_position"]:
                continue
        
        if filters.get("min_ranking_score") is not None:
            if combined_score < filters["min_ranking_score"]:
                continue
        
        if filters.get("required_skills"):
            required = set(s.lower() for s in filters["required_skills"])
            if not (required & resume_skills):
                continue
        
        candidates.append({
            "filename": filename,
            "rank_position": rank_position,
            "faiss_similarity": round(faiss_similarity, 4),
            "ranking_score": round(ranking_score, 4) if has_ranking else None,
            "skill_score": round(skill_score, 4),
            "combined_score": round(combined_score, 4),
            "skills": sorted(resume_skills),
            "excerpt": get_resume_text_excerpt(resume_path, max_chars=300)
        })
    
    # Sort by combined score
    candidates.sort(key=lambda x: x["combined_score"], reverse=True)
    
    # Return top_k
    return candidates[:top_k]
