"""
Rule-based NER extraction using regex and dictionaries.

Extracts:
- Skills (dictionary + regex)
- Degrees (regex)
- Dates (regex)
"""
import re
from typing import Dict, List, Set
from collections import defaultdict

from app.utils.skills import SKILLS, normalize_text
from app.utils.ner.base import ExtractedEntities, SkillMatch, EducationInfo, ExperienceInfo


# Degree patterns
DEGREE_PATTERNS = [
    r"\b(B\.?\s*Tech|B\.?\s*E|Bachelor\s+of\s+Technology|Bachelor\s+of\s+Engineering)\b",
    r"\b(M\.?\s*Tech|M\.?\s*E|Master\s+of\s+Technology|Master\s+of\s+Engineering)\b",
    r"\b(B\.?\s*S\.?\s*C|Bachelor\s+of\s+Science|B\.?\s*Sc)\b",
    r"\b(M\.?\s*S\.?\s*C|Master\s+of\s+Science|M\.?\s*Sc)\b",
    r"\b(B\.?\s*A|Bachelor\s+of\s+Arts)\b",
    r"\b(M\.?\s*A|Master\s+of\s+Arts)\b",
    r"\b(PhD|Ph\.?\s*D|Doctorate|Doctor\s+of\s+Philosophy)\b",
    r"\b(MBA|Master\s+of\s+Business\s+Administration)\b",
    r"\b(BBA|Bachelor\s+of\s+Business\s+Administration)\b"
]

# Date patterns
DATE_PATTERNS = [
    r"\b(19|20)\d{2}\b",  # YYYY (1900-2099)
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(19|20)\d{2}\b",  # Month YYYY
    r"\b(0?[1-9]|1[0-2])/(19|20)\d{2}\b",  # MM/YYYY
    r"\b(19|20)\d{2}-(0?[1-9]|1[0-2])\b",  # YYYY-MM
]

# Education field patterns
EDUCATION_FIELD_PATTERNS = [
    r"\b(Computer\s+Science|CS|C\.?\s*S)\b",
    r"\b(Software\s+Engineering|SE)\b",
    r"\b(Information\s+Technology|IT)\b",
    r"\b(Electrical\s+Engineering|EE|E\.?\s*E)\b",
    r"\b(Mechanical\s+Engineering|ME|M\.?\s*E)\b",
    r"\b(Data\s+Science|DS)\b",
    r"\b(Artificial\s+Intelligence|AI)\b",
    r"\b(Machine\s+Learning|ML)\b"
]


def extract_skills_with_context(text: str, skills_vocab: List[str], 
                                context_window: int = 40) -> Dict[str, SkillMatch]:
    """
    Extract skills with context information.
    
    Args:
        text: Input text
        skills_vocab: List of known skills
        context_window: Character window for context detection
        
    Returns:
        Dict mapping normalized skill to SkillMatch
    """
    normalized_text = normalize_text(text)
    skill_matches = defaultdict(lambda: {"count": 0, "contexts": set()})
    
    # Determine context (section) based on position
    # This is a simplified approach - in practice, we'd use section parser
    text_lower = text.lower()
    is_experience = any(keyword in text_lower for keyword in ["experience", "worked", "job", "position"])
    is_projects = any(keyword in text_lower for keyword in ["project", "built", "developed", "implemented"])
    is_skills = any(keyword in text_lower for keyword in ["skill", "technology", "tool", "proficient"])
    
    for skill in skills_vocab:
        skill_normalized = normalize_text(skill)
        
        # Count occurrences
        if ' ' in skill_normalized:
            # Multi-word skill: substring match
            count = normalized_text.count(skill_normalized)
            if count > 0:
                skill_matches[skill_normalized]["count"] += count
        else:
            # Single-word skill: word boundary match
            pattern = r'\b' + re.escape(skill_normalized) + r'\b'
            matches = re.findall(pattern, normalized_text, re.IGNORECASE)
            if matches:
                skill_matches[skill_normalized]["count"] += len(matches)
    
    # Section weights for confidence calculation
    SECTION_WEIGHTS = {
        "experience": 0.5,
        "skills": 0.3,
        "projects": 0.2,
        "other": 0.1
    }
    
    # Calculate total skill mentions for normalization
    total_mentions = sum(info["count"] for info in skill_matches.values())
    
    # Determine contexts and calculate confidence
    result = {}
    for skill, info in skill_matches.items():
        contexts = []
        context_weight = 0.0
        
        if is_experience:
            contexts.append("experience")
            context_weight += SECTION_WEIGHTS["experience"]
        if is_projects:
            contexts.append("projects")
            context_weight += SECTION_WEIGHTS["projects"]
        if is_skills:
            contexts.append("skills")
            context_weight += SECTION_WEIGHTS["skills"]
        if not contexts:
            contexts.append("other")
            context_weight = SECTION_WEIGHTS["other"]
        
        # Calculate confidence: normalized frequency × section weight
        # Normalized frequency: count / max(count, 1) clamped to [0, 1]
        # Then multiply by context weight
        normalized_freq = min(info["count"] / max(total_mentions, 1), 1.0) if total_mentions > 0 else 0.0
        confidence = normalized_freq * context_weight
        
        result[skill] = SkillMatch(
            skill=skill,
            count=info["count"],
            contexts=list(set(contexts)),
            confidence=round(confidence, 4)
        )
    
    return result


def extract_degrees(text: str) -> List[str]:
    """
    Extract degree mentions using regex.
    
    Args:
        text: Input text
        
    Returns:
        List of normalized degree strings
    """
    degrees = set()
    
    for pattern in DEGREE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]  # Take first group
            degree = match.strip().lower()
            # Normalize common variations
            degree = re.sub(r'\s+', ' ', degree)
            degree = re.sub(r'\.', '', degree)
            degrees.add(degree)
    
    return sorted(degrees)


def extract_dates(text: str) -> List[str]:
    """
    Extract date mentions and normalize to YYYY format.
    
    Args:
        text: Input text
        
    Returns:
        List of normalized date strings (YYYY format)
    """
    dates = set()
    
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                # Extract year from tuple
                year = match[-1] if match else None
                if year and len(year) == 2:
                    # Determine century
                    year_int = int(year)
                    if year_int >= 50:
                        year = "19" + year
                    else:
                        year = "20" + year
                elif year and len(year) == 4:
                    year = year
                else:
                    continue
            else:
                # Direct year match
                year_match = re.search(r"(19|20)\d{2}", match)
                if year_match:
                    year = year_match.group(0)
                else:
                    continue
            
            if year and 1900 <= int(year) <= 2099:
                dates.add(year)
    
    return sorted(dates)


def extract_education_field(text: str) -> List[str]:
    """
    Extract education field mentions.
    
    Args:
        text: Input text
        
    Returns:
        List of normalized field strings
    """
    fields = set()
    
    for pattern in EDUCATION_FIELD_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            field = match.strip().lower()
            field = re.sub(r'\s+', ' ', field)
            fields.add(field)
    
    return sorted(fields)


def extract_rule_based_entities(text: str, skills_vocab: List[str] = None) -> ExtractedEntities:
    """
    Extract entities using rule-based methods.
    
    Args:
        text: Input text
        skills_vocab: Optional list of skills (defaults to SKILLS)
        
    Returns:
        ExtractedEntities object
    """
    if skills_vocab is None:
        skills_vocab = SKILLS
    
    # Extract skills
    skills = extract_skills_with_context(text, skills_vocab)
    
    # Extract degrees
    degrees = extract_degrees(text)
    degree = degrees[0] if degrees else None
    
    # Extract education field
    education_fields = extract_education_field(text)
    education_field = education_fields[0] if education_fields else None
    
    # Extract dates
    dates = extract_dates(text)
    
    # Calculate experience years
    years_min = None
    years_max = None
    earliest_date = dates[0] if dates else None
    latest_date = dates[-1] if dates else None
    
    if earliest_date and latest_date:
        try:
            years_min = int(latest_date) - int(earliest_date)
            years_max = years_min  # Simplified - could be more sophisticated
        except (ValueError, TypeError):
            pass
    
    return ExtractedEntities(
        skills=skills,
        roles=[],  # Will be filled by spaCy NER
        organizations=[],  # Will be filled by spaCy NER
        education=EducationInfo(
            degree=degree,
            field=education_field
        ),
        experience=ExperienceInfo(
            years_min=years_min,
            years_max=years_max,
            earliest_date=earliest_date,
            latest_date=latest_date
        ),
        locations=[]  # Will be filled by spaCy NER
    )
