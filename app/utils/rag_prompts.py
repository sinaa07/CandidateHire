"""Prompt templates for RAG LLM queries."""
from typing import List, Dict


def build_system_prompt(has_ranking: bool = False) -> str:
    """
    Build system prompt for LLM.
    
    Args:
        has_ranking: Whether Phase 3 ranking is available
        
    Returns:
        System prompt string
    """
    ranking_note = "Ranking information from Phase 3 is available." if has_ranking else "No ranking information available."
    
    return f"""You are a recruitment assistant helping to answer questions about job candidates based on their resumes.
{ranking_note}
Answer questions based ONLY on the provided candidate information. Always cite the source filename when referencing specific candidates.
Be concise, accurate, and helpful."""


def build_user_prompt(
    query: str,
    candidates: List[Dict],
    include_context: bool = True
) -> str:
    """
    Build user prompt with candidate context.
    
    Args:
        query: User query
        candidates: List of candidate dictionaries
        include_context: Whether to include candidate context
        
    Returns:
        User prompt string
    """
    if not include_context or not candidates:
        return query
    
    context_parts = []
    for i, candidate in enumerate(candidates, 1):
        filename = candidate.get("filename", "unknown")
        rank = candidate.get("rank_position", "N/A")
        score = candidate.get("combined_score", 0.0)
        skills = ", ".join(candidate.get("skills", [])[:5])  # Top 5 skills
        excerpt = candidate.get("excerpt", "")
        
        context_part = f"""Candidate {i}:
- Filename: {filename}
- Rank: {rank}
- Score: {score}
- Skills: {skills}
- Excerpt: {excerpt}"""
        
        context_parts.append(context_part)
    
    context = "\n\n".join(context_parts)
    
    return f"""Candidates:
{context}

Question: {query}
Answer based on the candidates above:"""
