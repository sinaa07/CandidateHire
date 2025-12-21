import re

# Alias map for punctuated skills
ALIASES = {
    "c++": "cpp",
    "c#": "csharp",
    "node.js": "nodejs",
    "ci/cd": "cicd",
}

# Curated skill vocabulary (MVP) - using canonical forms
SKILLS = [
    "python", "java", "javascript", "typescript", "cpp", "csharp", "ruby", "go", "rust", "php",
    "sql", "nosql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "django", "flask", "fastapi", "spring", "react", "angular", "vue", "nodejs", "express",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible",
    "git", "cicd", "jenkins", "github actions", "gitlab",
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch",
    "agile", "scrum", "jira", "api", "rest", "graphql", "microservices",
    "html", "css", "sass", "webpack", "babel",
    "linux", "bash", "shell scripting", "nginx", "apache"
]

def canonicalize_text(text: str) -> str:
    """
    Replace common punctuated skill forms with stable aliases before normalization.
    
    Args:
        text: Input text
        
    Returns:
        Text with aliases applied
    """
    t = text.lower()
    for src, dst in ALIASES.items():
        t = t.replace(src, dst)
    return t

def normalize_text(text: str) -> str:
    """
    Normalize text for skill extraction.
    
    Args:
        text: Input text
        
    Returns:
        Normalized text (lowercase, punctuation replaced with spaces)
    """
    text = canonicalize_text(text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_skills(text: str, skills_vocab: list[str]) -> list[str]:
    """
    Extract skills from text using vocabulary matching.
    
    Args:
        text: Input text
        skills_vocab: List of skill keywords
        
    Returns:
        Sorted list of unique matched skills
    """
    normalized = normalize_text(text)
    matched_skills = set()
    
    for skill in skills_vocab:
        skill_normalized = normalize_text(skill)
        
        # For multi-word skills, use substring matching
        if ' ' in skill_normalized:
            if skill_normalized in normalized:
                matched_skills.add(skill_normalized)
        else:
            # For single-token skills, use word boundary matching
            pattern = r'\b' + re.escape(skill_normalized) + r'\b'
            if re.search(pattern, normalized):
                matched_skills.add(skill_normalized)
    
    return sorted(matched_skills)

def skill_overlap_score(jd_skills: set[str], resume_skills: set[str]) -> float:
    """
    Compute skill overlap score.
    
    Args:
        jd_skills: Skills from job description
        resume_skills: Skills from resume
        
    Returns:
        Score in [0, 1]
    """
    if not jd_skills:
        return 0.0
    
    intersection = jd_skills & resume_skills
    return len(intersection) / len(jd_skills)
