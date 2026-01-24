"""
Entity normalization - converts entities to canonical forms.

This module provides normalization for:
- Skills
- Organizations
- Roles
- Locations
- Degrees
"""
import re
from typing import Dict, List


# Organization normalization map (common aliases)
ORG_NORMALIZATIONS = {
    "amazon web services": "amazon",
    "aws": "amazon",
    "google cloud": "google",
    "gcp": "google",
    "microsoft azure": "microsoft",
    "azure": "microsoft",
    "meta": "facebook",
    "meta platforms": "facebook",
}


# Skill normalization (handled in skills.py, but we add some here)
SKILL_NORMALIZATIONS = {
    "python3": "python",
    "python 3": "python",
    "js": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "c#": "csharp",
    "node.js": "nodejs",
    "node js": "nodejs",
}


def normalize_skill(skill: str) -> str:
    """
    Normalize skill name to canonical form.
    
    Args:
        skill: Skill name
        
    Returns:
        Normalized skill name
    """
    skill_lower = skill.lower().strip()
    
    # Check normalization map
    if skill_lower in SKILL_NORMALIZATIONS:
        return SKILL_NORMALIZATIONS[skill_lower]
    
    # Remove version numbers
    skill_lower = re.sub(r'\s*\d+(\.\d+)*\s*$', '', skill_lower)
    
    # Remove extra whitespace
    skill_lower = re.sub(r'\s+', ' ', skill_lower).strip()
    
    return skill_lower


def normalize_organization(org: str) -> str:
    """
    Normalize organization name to canonical form.
    
    Args:
        org: Organization name
        
    Returns:
        Normalized organization name
    """
    org_lower = org.lower().strip()
    
    # Remove common suffixes
    org_lower = re.sub(r'\s+(inc|llc|ltd|corp|corporation|company|co)\.?$', '', org_lower)
    
    # Check normalization map
    if org_lower in ORG_NORMALIZATIONS:
        return ORG_NORMALIZATIONS[org_lower]
    
    # Remove extra whitespace
    org_lower = re.sub(r'\s+', ' ', org_lower).strip()
    
    return org_lower


def normalize_role(role: str) -> str:
    """
    Normalize role/title to canonical form.
    
    Args:
        role: Role/title string
        
    Returns:
        Normalized role name
    """
    role_lower = role.lower().strip()
    
    # Normalize common variations
    role_lower = re.sub(r'\s+', ' ', role_lower)
    
    # Remove extra whitespace
    role_lower = role_lower.strip()
    
    return role_lower


def normalize_location(location: str) -> str:
    """
    Normalize location name.
    
    Args:
        location: Location name
        
    Returns:
        Normalized location name
    """
    location_lower = location.lower().strip()
    
    # Remove extra whitespace
    location_lower = re.sub(r'\s+', ' ', location_lower).strip()
    
    return location_lower


def normalize_degree(degree: str) -> str:
    """
    Normalize degree name.
    
    Args:
        degree: Degree string
        
    Returns:
        Normalized degree name
    """
    degree_lower = degree.lower().strip()
    
    # Remove dots and normalize spacing
    degree_lower = re.sub(r'\.', '', degree_lower)
    degree_lower = re.sub(r'\s+', ' ', degree_lower).strip()
    
    # Common normalizations
    degree_lower = re.sub(r'\bb\.?\s*tech\b', 'btech', degree_lower)
    degree_lower = re.sub(r'\bm\.?\s*tech\b', 'mtech', degree_lower)
    degree_lower = re.sub(r'\bb\.?\s*sc\b', 'bsc', degree_lower)
    degree_lower = re.sub(r'\bm\.?\s*sc\b', 'msc', degree_lower)
    
    return degree_lower


def normalize_entities(entities: Dict) -> Dict:
    """
    Normalize all entities in the extracted entities dict.
    
    Args:
        entities: Dict with entity data (from ExtractedEntities.to_dict())
        
    Returns:
        Normalized entities dict
    """
    normalized = {}
    
    # Normalize skills
    if "skills" in entities:
        normalized_skills = {}
        for skill, info in entities["skills"].items():
            norm_skill = normalize_skill(skill)
            normalized_skills[norm_skill] = info
        normalized["skills"] = normalized_skills
    else:
        normalized["skills"] = {}
    
    # Normalize roles
    if "roles" in entities:
        normalized["roles"] = [normalize_role(r) for r in entities["roles"]]
    else:
        normalized["roles"] = []
    
    # Normalize organizations
    if "organizations" in entities:
        normalized["organizations"] = [normalize_organization(o) for o in entities["organizations"]]
    else:
        normalized["organizations"] = []
    
    # Normalize locations
    if "locations" in entities:
        normalized["locations"] = [normalize_location(l) for l in entities["locations"]]
    else:
        normalized["locations"] = []
    
    # Normalize education
    if "education" in entities:
        education = entities["education"].copy()
        if education.get("degree"):
            education["degree"] = normalize_degree(education["degree"])
        normalized["education"] = education
    else:
        normalized["education"] = {}
    
    # Copy experience as-is (already normalized)
    if "experience" in entities:
        normalized["experience"] = entities["experience"]
    else:
        normalized["experience"] = {}
    
    return normalized
