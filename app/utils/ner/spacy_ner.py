"""
spaCy-based NER extraction for organizations, roles, and locations.

Uses lightweight spaCy model (en_core_web_sm) for controlled extraction.
"""
import logging
from typing import List, Set, Optional

logger = logging.getLogger(__name__)

# Global spaCy model (lazy loaded)
_nlp = None


def _get_spacy_model():
    """
    Get or load spaCy model (singleton pattern).
    
    Returns:
        spaCy language model
    """
    global _nlp
    
    if _nlp is None:
        try:
            import spacy
            # Load small English model, disable parser and lemmatizer for speed
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
            logger.info("spaCy model loaded successfully")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
            _nlp = None
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            _nlp = None
    
    return _nlp


def extract_organizations(text: str, min_length: int = 3) -> List[str]:
    """
    Extract organization entities using spaCy NER.
    
    Args:
        text: Input text
        min_length: Minimum organization name length (filters short false positives)
        
    Returns:
        List of normalized organization names
    """
    nlp = _get_spacy_model()
    if nlp is None:
        return []
    
    try:
        doc = nlp(text)
        orgs = set()
        
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org_name = ent.text.strip()
                # Filter short organizations (likely false positives)
                if len(org_name) >= min_length:
                    orgs.add(org_name.lower())
        
        return sorted(orgs)
    except Exception as e:
        logger.warning(f"spaCy NER extraction failed: {e}")
        return []


def extract_organizations_from_doc(doc, min_length: int = 3) -> List[str]:
    """
    Extract organizations from a pre-processed spaCy doc.
    
    Args:
        doc: spaCy Doc object
        min_length: Minimum organization name length
        
    Returns:
        List of normalized organization names
    """
    orgs = set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org_name = ent.text.strip()
            if len(org_name) >= min_length:
                orgs.add(org_name.lower())
    return sorted(orgs)


# Role allow-list: only accept roles containing these keywords
# This filters out junk like "member", "associate", "professional"
ROLE_ALLOW_LIST = {
    "engineer", "developer", "analyst", "manager", "architect", 
    "scientist", "specialist", "consultant", "lead", "director"
}


def _is_valid_role(role: str) -> bool:
    """
    Check if role contains allowed keywords.
    
    Args:
        role: Role string to validate
        
    Returns:
        True if role is valid, False otherwise
    """
    role_lower = role.lower()
    return any(keyword in role_lower for keyword in ROLE_ALLOW_LIST)


def extract_roles_titles(text: str) -> List[str]:
    """
    Extract role/title entities using heuristics and spaCy.
    
    Never trusts spaCy roles blindly - uses allow-list filter.
    
    Args:
        text: Input text
        
    Returns:
        List of normalized role/title strings (filtered by allow-list)
    """
    # Common role patterns (regex-based)
    import re
    
    role_patterns = [
        r"\b(Senior|Junior|Lead|Principal|Staff|Associate)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(Engineer|Developer|Architect|Manager|Analyst|Scientist|Specialist)\b",
        r"\b(Software|Backend|Frontend|Full\s+Stack|DevOps|Data|ML|AI)\s+(Engineer|Developer|Architect)\b"
    ]
    
    roles = set()
    
    for pattern in role_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                # Combine tuple groups
                role = ' '.join(m for m in match if m).strip()
            else:
                role = match.strip()
            
            if role and len(role) > 3 and _is_valid_role(role):
                roles.add(role.lower())
    
    # Also use spaCy for capitalized phrases that might be titles
    nlp = _get_spacy_model()
    if nlp:
        try:
            doc = nlp(text)
            # Look for capitalized phrases that might be titles
            for token in doc:
                if token.is_title and len(token.text) > 3:
                    # Check if it's followed by common role words
                    if token.i + 1 < len(doc):
                        next_token = doc[token.i + 1]
                        if next_token.text.lower() in ["engineer", "developer", "manager", "analyst", 
                                                       "architect", "scientist", "specialist"]:
                            role = f"{token.text} {next_token.text}".lower()
                            if _is_valid_role(role):
                                roles.add(role)
        except Exception:
            pass
    
    return sorted(roles)


def extract_locations(text: str) -> List[str]:
    """
    Extract location entities using spaCy NER.
    
    Args:
        text: Input text
        
    Returns:
        List of normalized location names
    """
    nlp = _get_spacy_model()
    if nlp is None:
        return []
    
    try:
        doc = nlp(text)
        locations = set()
        
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:  # Geopolitical entity or location
                loc_name = ent.text.strip()
                if len(loc_name) >= 2:  # Filter very short locations
                    locations.add(loc_name.lower())
        
        return sorted(locations)
    except Exception as e:
        logger.warning(f"spaCy location extraction failed: {e}")
        return []


def extract_locations_from_doc(doc) -> List[str]:
    """
    Extract locations from a pre-processed spaCy doc.
    
    Args:
        doc: spaCy Doc object
        
    Returns:
        List of normalized location names
    """
    locations = set()
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            loc_name = ent.text.strip()
            if len(loc_name) >= 2:
                locations.add(loc_name.lower())
    return sorted(locations)


def extract_spacy_entities(text: str) -> dict:
    """
    Extract all spaCy-based entities.
    
    Optimized single-pass version: processes text through spaCy once.
    
    Args:
        text: Input text
        
    Returns:
        Dict with keys: organizations, roles, locations
    """
    nlp = _get_spacy_model()
    if nlp is None:
        # Fallback to individual functions if model not available
        return {
            "organizations": extract_organizations(text),
            "roles": extract_roles_titles(text),
            "locations": extract_locations(text)
        }
    
    try:
        # Single pass: process text once
        doc = nlp(text)
        
        # Extract all entities in one pass
        orgs = set()
        locations = set()
        
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org_name = ent.text.strip()
                if len(org_name) >= 3:  # min_length
                    orgs.add(org_name.lower())
            elif ent.label_ in ["GPE", "LOC"]:
                loc_name = ent.text.strip()
                if len(loc_name) >= 2:
                    locations.add(loc_name.lower())
        
        # Extract roles (uses regex + spaCy token analysis)
        roles = set()
        import re
        
        # Regex-based role patterns
        role_patterns = [
            r"\b(Senior|Junior|Lead|Principal|Staff|Associate)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(Engineer|Developer|Architect|Manager|Analyst|Scientist|Specialist)\b",
            r"\b(Software|Backend|Frontend|Full\s+Stack|DevOps|Data|ML|AI)\s+(Engineer|Developer|Architect)\b"
        ]
        
        for pattern in role_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    role = ' '.join(m for m in match if m).strip()
                else:
                    role = match.strip()
                
                if role and len(role) > 3 and _is_valid_role(role):
                    roles.add(role.lower())
        
        # Use spaCy tokens for role detection (from pre-processed doc)
        for token in doc:
            if token.is_title and len(token.text) > 3:
                if token.i + 1 < len(doc):
                    next_token = doc[token.i + 1]
                    if next_token.text.lower() in ["engineer", "developer", "manager", "analyst", 
                                                   "architect", "scientist", "specialist"]:
                        role = f"{token.text} {next_token.text}".lower()
                        if _is_valid_role(role):
                            roles.add(role)
        
        return {
            "organizations": sorted(orgs),
            "roles": sorted(roles),
            "locations": sorted(locations)
        }
    except Exception as e:
        logger.warning(f"spaCy single-pass extraction failed: {e}, falling back to individual functions")
        # Fallback to original method
        return {
            "organizations": extract_organizations(text),
            "roles": extract_roles_titles(text),
            "locations": extract_locations(text)
        }
