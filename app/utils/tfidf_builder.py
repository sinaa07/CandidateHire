"""
Section-aware TF-IDF builder with n-grams and skill boosting.

This module provides improved TF-IDF vectorization that:
- Splits resumes into sections with weighted importance
- Uses n-grams (1-3) for phrase matching
- Boosts skill-related tokens
"""
from typing import Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import scipy.sparse

from app.utils.section_parser import ResumeSections, sections_to_dict
from app.utils.skills import SKILLS, normalize_text


# Section weights for TF-IDF combination
SECTION_WEIGHTS = {
    "experience": 0.5,
    "skills": 0.3,
    "projects": 0.2,
    "summary": 0.0,  # Not used in scoring but available
    "education": 0.0,  # Not used in scoring but available
    "other": 0.0  # Not used in scoring but available
}


def build_section_vectorizer(min_df: int = 1) -> TfidfVectorizer:
    """
    Build TF-IDF vectorizer optimized for resume sections.
    
    Features:
    - n-grams (1-3) for phrase matching
    - min_df to filter rare terms (default 1, but can be adjusted)
    - sublinear_tf for better term frequency scaling
    - English stop words
    
    Args:
        min_df: Minimum document frequency (default 1 to avoid empty vocabulary)
    
    Returns:
        Configured TfidfVectorizer
    """
    return TfidfVectorizer(
        ngram_range=(1, 3),
        min_df=min_df,
        stop_words="english",
        sublinear_tf=True,
        lowercase=True
    )


def _compute_skill_boost_factor(resume_text: str, jd_text: str, skills_vocab: List[str]) -> float:
    """
    Compute skill boost factor based on skill overlap.
    
    This is applied POST-cosine similarity to avoid breaking vector space assumptions.
    
    Args:
        resume_text: Resume text
        jd_text: Job description text
        skills_vocab: List of known skills
        
    Returns:
        Boost factor (1.0 = no boost, >1.0 = boosted)
    """
    from app.utils.skills import extract_skills
    
    resume_skills = set(extract_skills(resume_text, skills_vocab))
    jd_skills = set(extract_skills(jd_text, skills_vocab))
    
    if not jd_skills:
        return 1.0
    
    # Calculate skill overlap ratio
    overlap = len(resume_skills & jd_skills) / len(jd_skills)
    
    # Boost factor: 1.0 (no boost) to 1.5 (max boost)
    # Linear scaling: 0% overlap → 1.0, 100% overlap → 1.5
    boost_factor = 1.0 + (overlap * 0.5)
    
    return boost_factor


def build_section_aware_tfidf(resume_sections_list: List[ResumeSections], 
                               skills_vocab: Optional[List[str]] = None) -> Dict[str, TfidfVectorizer]:
    """
    Build separate TF-IDF vectorizers for each weighted section.
    
    Args:
        resume_sections_list: List of ResumeSections objects
        skills_vocab: Optional list of skills for boosting
        
    Returns:
        Dict mapping section name to fitted TfidfVectorizer
    """
    if skills_vocab is None:
        skills_vocab = SKILLS
    
    vectorizers = {}
    
    # Build vectorizer for each weighted section
    for section_name in ["experience", "skills", "projects"]:
        if section_name not in SECTION_WEIGHTS:
            continue
        
        # Extract section texts
        section_texts = []
        for sections in resume_sections_list:
            section_dict = sections_to_dict(sections)
            section_text = section_dict.get(section_name, "").strip()
            # Only add non-empty texts
            if section_text:
                section_texts.append(section_text)
        
        # Skip if no valid section texts
        if not section_texts:
            continue
        
        # Adjust min_df based on number of documents
        # Use min_df=2 if we have enough documents, otherwise min_df=1
        num_docs = len(section_texts)
        min_df = 2 if num_docs >= 3 else 1
        
        # Build and fit vectorizer
        vectorizer = build_section_vectorizer(min_df=min_df)
        
        try:
            vectorizer.fit(section_texts)
            
            # Check if vocabulary is empty
            if len(vectorizer.vocabulary_) == 0:
                # Fallback: use min_df=1 and try again
                vectorizer = build_section_vectorizer(min_df=1)
                vectorizer.fit(section_texts)
                
                # If still empty, skip this section
                if len(vectorizer.vocabulary_) == 0:
                    continue
            
            vectorizers[section_name] = vectorizer
        except ValueError as e:
            # Handle empty vocabulary error
            if "empty vocabulary" in str(e).lower() or "only contain stop words" in str(e).lower():
                # Try with min_df=1
                try:
                    vectorizer = build_section_vectorizer(min_df=1)
                    vectorizer.fit(section_texts)
                    if len(vectorizer.vocabulary_) > 0:
                        vectorizers[section_name] = vectorizer
                except ValueError:
                    # Skip this section if it still fails
                    continue
            else:
                raise
    
    return vectorizers


def transform_sections(sections: ResumeSections, 
                       vectorizers: Dict[str, TfidfVectorizer],
                       skills_vocab: Optional[List[str]] = None) -> Dict[str, scipy.sparse.csr_matrix]:
    """
    Transform resume sections into TF-IDF vectors.
    
    Args:
        sections: ResumeSections object
        vectorizers: Dict of fitted vectorizers per section
        skills_vocab: Optional list of skills (not used for vector modification)
        
    Returns:
        Dict mapping section name to sparse TF-IDF vector
    """
    section_dict = sections_to_dict(sections)
    vectors = {}
    
    for section_name, vectorizer in vectorizers.items():
        section_text = section_dict.get(section_name, "")
        vector = vectorizer.transform([section_text])
        vectors[section_name] = vector
    
    return vectors


def transform_jd_sections(jd_text: str, 
                          vectorizers: Dict[str, TfidfVectorizer],
                          skills_vocab: Optional[List[str]] = None) -> Dict[str, scipy.sparse.csr_matrix]:
    """
    Transform job description into section vectors.
    
    Note: JD is treated as a single document, so we use the same text
    for all section vectorizers.
    
    Args:
        jd_text: Job description text
        vectorizers: Dict of fitted vectorizers per section
        skills_vocab: Optional list of skills (not used for vector modification)
        
    Returns:
        Dict mapping section name to sparse TF-IDF vector
    """
    vectors = {}
    
    if not jd_text or not jd_text.strip():
        # Return empty vectors for all sections if JD is empty
        for section_name, vectorizer in vectorizers.items():
            vectors[section_name] = scipy.sparse.csr_matrix((1, len(vectorizer.vocabulary_)))
        return vectors
    
    for section_name, vectorizer in vectorizers.items():
        try:
            vector = vectorizer.transform([jd_text])
            vectors[section_name] = vector
        except Exception as e:
            # If transformation fails (e.g., vocabulary mismatch), create empty vector
            # This can happen if JD text doesn't match any terms in the vocabulary
            vectors[section_name] = scipy.sparse.csr_matrix((1, len(vectorizer.vocabulary_)))
    
    return vectors


def compute_section_aware_similarity(resume_vectors: Dict[str, scipy.sparse.csr_matrix],
                                     jd_vectors: Dict[str, scipy.sparse.csr_matrix],
                                     resume_text: str = "",
                                     jd_text: str = "",
                                     skills_vocab: Optional[List[str]] = None) -> float:
    """
    Compute weighted cosine similarity across sections with post-cosine skill boosting.
    
    Args:
        resume_vectors: Dict of section vectors for resume
        jd_vectors: Dict of section vectors for JD
        resume_text: Resume text (for skill boost calculation)
        jd_text: Job description text (for skill boost calculation)
        skills_vocab: Optional list of skills for boosting
        
    Returns:
        Weighted similarity score [0, 1] with skill boost applied
    """
    if skills_vocab is None:
        skills_vocab = SKILLS
    
    total_score = 0.0
    total_weight = 0.0
    
    for section_name in ["experience", "skills", "projects"]:
        if section_name not in SECTION_WEIGHTS:
            continue
        
        weight = SECTION_WEIGHTS[section_name]
        if weight == 0.0:
            continue
        
        if section_name in resume_vectors and section_name in jd_vectors:
            resume_vec = resume_vectors[section_name]
            jd_vec = jd_vectors[section_name]
            
            # Compute cosine similarity
            similarity = cosine_similarity(jd_vec, resume_vec)[0, 0]
            
            # Weighted contribution
            total_score += weight * similarity
            total_weight += weight
    
    # Normalize by total weight
    base_similarity = total_score / total_weight if total_weight > 0 else 0.0
    
    # Apply skill boost POST-cosine (safer, reversible)
    if resume_text and jd_text:
        skill_boost = _compute_skill_boost_factor(resume_text, jd_text, skills_vocab)
        return min(base_similarity * skill_boost, 1.0)
    
    return base_similarity


def build_combined_resume_text(sections: ResumeSections) -> str:
    """
    Build combined resume text from weighted sections.
    
    This is a fallback for backward compatibility with existing code.
    
    Args:
        sections: ResumeSections object
        
    Returns:
        Combined text string
    """
    section_dict = sections_to_dict(sections)
    
    # Combine weighted sections
    parts = []
    for section_name in ["experience", "skills", "projects"]:
        text = section_dict.get(section_name, "")
        if text:
            parts.append(text)
    
    # Add other sections
    for section_name in ["summary", "education", "other"]:
        text = section_dict.get(section_name, "")
        if text:
            parts.append(text)
    
    return '\n\n'.join(parts)
