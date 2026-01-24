"""
Experience depth and stability calculations.

This module computes:
- Experience depth score (based on years)
- Stability proxy (based on role count)
"""
from typing import Optional
from app.utils.ner.base import ExtractedEntities, ExperienceInfo


def calculate_experience_depth(years: Optional[int]) -> float:
    """
    Calculate experience depth score.
    
    Formula: min(years / 10, 1.0)
    - 0 years → 0.0
    - 5 years → 0.5
    - 10+ years → 1.0
    
    Years are clamped to max 20 to prevent inflated resumes from skewing Pareto later.
    
    Args:
        years: Years of experience
        
    Returns:
        Score in [0, 1]
    """
    if years is None or years < 0:
        return 0.0
    
    # Clamp years to reasonable max (prevents inflated resumes)
    years = min(years, 20)
    
    return min(years / 10.0, 1.0)


def calculate_stability(role_count: int) -> float:
    """
    Calculate stability proxy score.
    
    Formula: 1 / (1 + role_count / 5)
    - 1 role → ~0.83
    - 5 roles → 0.5
    - 10 roles → ~0.33
    
    Lower role count = higher stability.
    
    Args:
        role_count: Number of roles/positions
        
    Returns:
        Stability score in [0, 1]
    """
    if role_count <= 0:
        return 1.0
    
    return 1.0 / (1.0 + role_count / 5.0)


def compute_experience_signals(entities: ExtractedEntities) -> dict:
    """
    Compute all experience-related signals.
    
    Args:
        entities: ExtractedEntities object
        
    Returns:
        Dict with experience_depth, stability, and raw values
    """
    # Extract years from experience info
    years = entities.experience.years_min
    if years is None:
        years = entities.experience.years_max
    
    # Calculate depth
    experience_depth = calculate_experience_depth(years)
    
    # Calculate stability (based on role count)
    role_count = len(entities.roles)
    stability = calculate_stability(role_count)
    
    return {
        "experience_depth": round(experience_depth, 4),
        "stability": round(stability, 4),
        "years_min": entities.experience.years_min,
        "years_max": entities.experience.years_max,
        "role_count": role_count,
        "earliest_date": entities.experience.earliest_date,
        "latest_date": entities.experience.latest_date
    }
