# FILE: app/utils/validation.py
from app.models.enums import ResumeStatus

def validate_text(text: str) -> ResumeStatus:
    """
    Decide validation state from extracted text.
    
    Args:
        text: Extracted text content
        
    Returns:
        ResumeStatus: Either EMPTY or OK
    """
    if not text or text.isspace():
        return ResumeStatus.EMPTY
    return ResumeStatus.OK