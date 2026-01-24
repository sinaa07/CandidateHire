"""
Base data structures for NER extraction.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SkillMatch:
    """Skill entity match."""
    skill: str
    count: int
    contexts: List[str]  # e.g., ["experience", "projects"]
    confidence: float = 0.0  # Confidence score [0, 1]


@dataclass
class EducationInfo:
    """Education information."""
    degree: Optional[str] = None
    field: Optional[str] = None


@dataclass
class ExperienceInfo:
    """Experience timeline information."""
    years_min: Optional[int] = None
    years_max: Optional[int] = None
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None


@dataclass
class ExtractedEntities:
    """
    Structured extracted entities from resume.
    
    All entities are normalized and stored in canonical form.
    """
    skills: Dict[str, SkillMatch] = field(default_factory=dict)
    roles: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    education: EducationInfo = field(default_factory=EducationInfo)
    experience: ExperienceInfo = field(default_factory=ExperienceInfo)
    locations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "skills": {
                skill: {
                    "count": match.count,
                    "contexts": match.contexts,
                    "confidence": match.confidence
                }
                for skill, match in self.skills.items()
            },
            "roles": self.roles,
            "organizations": self.organizations,
            "education": {
                "degree": self.education.degree,
                "field": self.education.field
            },
            "experience": {
                "years_min": self.experience.years_min,
                "years_max": self.experience.years_max,
                "earliest_date": self.experience.earliest_date,
                "latest_date": self.experience.latest_date
            },
            "locations": self.locations
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ExtractedEntities":
        """Create from dictionary."""
        skills = {}
        for skill, info in data.get("skills", {}).items():
            skills[skill] = SkillMatch(
                skill=skill,
                count=info.get("count", 0),
                contexts=info.get("contexts", []),
                confidence=info.get("confidence", 0.0)
            )
        
        education_data = data.get("education", {})
        education = EducationInfo(
            degree=education_data.get("degree"),
            field=education_data.get("field")
        )
        
        experience_data = data.get("experience", {})
        experience = ExperienceInfo(
            years_min=experience_data.get("years_min"),
            years_max=experience_data.get("years_max"),
            earliest_date=experience_data.get("earliest_date"),
            latest_date=experience_data.get("latest_date")
        )
        
        return cls(
            skills=skills,
            roles=data.get("roles", []),
            organizations=data.get("organizations", []),
            education=education,
            experience=experience,
            locations=data.get("locations", [])
        )
