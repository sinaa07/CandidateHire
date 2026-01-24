"""
Resume section parser - converts raw resume text into structured sections.

This module provides deterministic, regex-based section parsing without ML.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Union, Tuple


@dataclass
class ResumeSections:
    """Structured resume sections."""
    summary: str
    experience: str
    skills: str
    education: str
    projects: str
    other: str


# Common section heading patterns (case-insensitive)
SECTION_PATTERNS = {
    "summary": [
        r"^(summary|profile|objective|about|overview|executive\s+summary)",
        r"^(professional\s+summary|career\s+summary|summary\s+of\s+qualifications)"
    ],
    "experience": [
        r"^(experience|work\s+experience|employment|professional\s+experience|work\s+history)",
        r"^(career\s+history|employment\s+history|professional\s+background)"
    ],
    "skills": [
        r"^(skills|technical\s+skills|core\s+skills|competencies|expertise)",
        r"^(key\s+skills|skill\s+set|technologies|tools\s+and\s+technologies)"
    ],
    "education": [
        r"^(education|academic\s+background|qualifications|academic\s+qualifications)",
        r"^(educational\s+background|degrees|academics)"
    ],
    "projects": [
        r"^(projects|key\s+projects|notable\s+projects|project\s+experience)",
        r"^(selected\s+projects|project\s+portfolio)"
    ]
}


def _normalize_text(text: str) -> str:
    """Normalize text for section matching."""
    return text.strip()


def _find_section_boundaries(text: str) -> Dict[str, List[tuple]]:
    """
    Find all section headings and their line positions.
    
    Returns:
        Dict mapping section name to list of (line_index, heading_text) tuples
    """
    lines = text.split('\n')
    boundaries = {section: [] for section in SECTION_PATTERNS.keys()}
    boundaries["other"] = []
    
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check each section pattern
        matched = False
        for section, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    boundaries[section].append((idx, line_stripped))
                    matched = True
                    break
            if matched:
                break
        
        # If no section matched and line looks like a heading (short, uppercase, or title case)
        if not matched and len(line_stripped) < 50:
            # Check if it might be a heading (all caps or title case)
            if line_stripped.isupper() or (line_stripped.istitle() and len(line_stripped.split()) <= 5):
                boundaries["other"].append((idx, line_stripped))
    
    return boundaries


def _extract_section_content(text: str, start_line: int, end_line: int) -> str:
    """Extract content between two line indices."""
    lines = text.split('\n')
    if start_line >= len(lines):
        return ""
    
    end_idx = min(end_line, len(lines))
    section_lines = lines[start_line:end_idx]
    return '\n'.join(section_lines).strip()


def parse_sections(text: str, return_boundaries: bool = False) -> Union[ResumeSections, Tuple[ResumeSections, Dict[str, List[List[int]]]]]:
    """
    Parse resume text into structured sections.
    
    Rules:
    - Case-insensitive heading matching
    - Regex-based (no ML)
    - Merge duplicate headings
    - Never return None → empty string instead
    - Preserve original text inside sections
    
    Args:
        text: Raw resume text
        return_boundaries: If True, also return section boundaries as line indices
        
    Returns:
        ResumeSections object with all sections populated.
        If return_boundaries=True, returns tuple of (ResumeSections, boundaries_dict)
        where boundaries_dict maps section name to list of [start_line, end_line] pairs.
    """
    if not text or not text.strip():
        return ResumeSections(
            summary="",
            experience="",
            skills="",
            education="",
            projects="",
            other=""
        )
    
    # Find all section boundaries
    boundaries = _find_section_boundaries(text)
    lines = text.split('\n')
    
    # Build section content
    sections_content = {
        "summary": [],
        "experience": [],
        "skills": [],
        "education": [],
        "projects": [],
        "other": []
    }
    
    # Process each section type
    for section_name in ["summary", "experience", "skills", "education", "projects"]:
        if not boundaries[section_name]:
            continue
        
        # Sort by line index
        section_starts = sorted(boundaries[section_name], key=lambda x: x[0])
        
        for i, (line_idx, heading) in enumerate(section_starts):
            # Find end of this section (next section start or end of document)
            next_start = len(lines)
            
            # Check for next section of any type
            all_starts = []
            for other_section, other_starts in boundaries.items():
                if other_section != section_name:
                    all_starts.extend([(idx, other_section) for idx, _ in other_starts])
            
            # Also check next occurrence of same section
            if i + 1 < len(section_starts):
                all_starts.append((section_starts[i + 1][0], section_name))
            
            if all_starts:
                # Filter to only indices greater than current line
                next_indices = [idx for idx, _ in all_starts if idx > line_idx]
                if next_indices:
                    next_start = min(next_indices)
            
            # Extract content (skip the heading line itself)
            content_start = line_idx + 1
            content = _extract_section_content(text, content_start, next_start)
            
            if content:
                sections_content[section_name].append(content)
    
    # Merge duplicate sections
    merged = {}
    for section_name, contents in sections_content.items():
        merged[section_name] = '\n\n'.join(contents).strip()
    
    # Collect remaining content as "other"
    # This includes content before first section and between sections
    all_section_lines = set()
    for section_starts in boundaries.values():
        for line_idx, _ in section_starts:
            all_section_lines.add(line_idx)
    
    # Extract "other" content (lines not part of any section)
    other_lines = []
    in_section = False
    current_section_end = len(lines)
    
    for idx, line in enumerate(lines):
        if idx in all_section_lines:
            # This is a section heading, skip it and mark we're in a section
            in_section = True
            # Find when this section ends
            for section_starts in boundaries.values():
                for sec_idx, _ in section_starts:
                    if sec_idx > idx:
                        current_section_end = min(current_section_end, sec_idx)
            continue
        
        if idx >= current_section_end:
            in_section = False
            current_section_end = len(lines)
        
        if not in_section and line.strip():
            other_lines.append(line)
    
    merged["other"] = '\n'.join(other_lines).strip()
    
    sections = ResumeSections(
        summary=merged.get("summary", ""),
        experience=merged.get("experience", ""),
        skills=merged.get("skills", ""),
        education=merged.get("education", ""),
        projects=merged.get("projects", ""),
        other=merged.get("other", "")
    )
    
    if return_boundaries:
        # Build boundaries dict with [start_line, end_line] pairs for each section
        boundaries_dict: Dict[str, List[List[int]]] = {}
        
        for section_name in ["summary", "experience", "skills", "education", "projects"]:
            if not boundaries[section_name]:
                boundaries_dict[section_name] = []
                continue
            
            section_starts = sorted(boundaries[section_name], key=lambda x: x[0])
            section_ranges = []
            
            for i, (line_idx, heading) in enumerate(section_starts):
                # Find end of this section
                next_start = len(lines)
                
                # Check for next section of any type
                all_starts = []
                for other_section, other_starts in boundaries.items():
                    if other_section != section_name:
                        all_starts.extend([(idx, other_section) for idx, _ in other_starts])
                
                # Also check next occurrence of same section
                if i + 1 < len(section_starts):
                    all_starts.append((section_starts[i + 1][0], section_name))
                
                if all_starts:
                    # Filter to only indices greater than current line
                    next_indices = [idx for idx, _ in all_starts if idx > line_idx]
                    if next_indices:
                        next_start = min(next_indices)
                
                section_ranges.append([line_idx, next_start])
            
            boundaries_dict[section_name] = section_ranges
        
        # For "other" section, collect all non-section lines
        other_ranges = []
        if other_lines:
            # Find ranges of consecutive other lines
            other_line_indices = []
            for idx, line in enumerate(lines):
                if idx not in all_section_lines and line.strip():
                    other_line_indices.append(idx)
            
            if other_line_indices:
                # Group consecutive indices
                ranges = []
                start = other_line_indices[0]
                for i in range(1, len(other_line_indices)):
                    if other_line_indices[i] != other_line_indices[i-1] + 1:
                        ranges.append([start, other_line_indices[i-1] + 1])
                        start = other_line_indices[i]
                ranges.append([start, other_line_indices[-1] + 1])
                boundaries_dict["other"] = ranges
            else:
                boundaries_dict["other"] = []
        else:
            boundaries_dict["other"] = []
        
        return sections, boundaries_dict
    
    return sections


def sections_to_dict(sections: ResumeSections, boundaries: Dict[str, List[List[int]]] = None) -> Dict:
    """
    Convert ResumeSections to dictionary with optional metadata.
    
    Args:
        sections: ResumeSections object
        boundaries: Optional dict mapping section name to list of [start_line, end_line] pairs
        
    Returns:
        Dictionary with sections and optional _meta field
    """
    result = {
        "summary": sections.summary,
        "experience": sections.experience,
        "skills": sections.skills,
        "education": sections.education,
        "projects": sections.projects,
        "other": sections.other
    }
    
    # Add metadata if boundaries provided
    if boundaries:
        result["_meta"] = {
            f"{section}_lines": lines
            for section, lines in boundaries.items()
            if lines
        }
    
    return result