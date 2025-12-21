def combine_scores(tfidf_score: float, skill_score: float, w_tfidf: float = 0.7, w_skill: float = 0.3) -> float:
    """
    Combine scoring components into final score.
    
    Args:
        tfidf_score: TF-IDF cosine similarity score
        skill_score: Skill overlap score
        w_tfidf: Weight for TF-IDF score
        w_skill: Weight for skill score
        
    Returns:
        Weighted combined score (clamped to [0, 1])
    """
    final_score = (w_tfidf * tfidf_score) + (w_skill * skill_score)
    return max(0.0, min(1.0, final_score))

def build_explainability(jd_skills: list[str], resume_skills: list[str]) -> dict:
    """
    Build explainability payload.
    
    Args:
        jd_skills: Skills extracted from JD
        resume_skills: Skills extracted from resume
        
    Returns:
        Dictionary with matched and missing skills
    """
    jd_set = set(jd_skills)
    resume_set = set(resume_skills)
    
    matched = sorted(jd_set & resume_set)
    missing = sorted(jd_set - resume_set)
    
    return {
        "jd_skills": jd_skills,
        "resume_skills": resume_skills,
        "matched_skills": matched,
        "missing_skills": missing
    }
