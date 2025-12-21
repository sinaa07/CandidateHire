import hashlib

def compute_sha256(text: str) -> str:
    """
    Compute SHA-256 hash of text content.
    
    Args:
        text: Extracted text content
        
    Returns:
        str: Hexadecimal hash string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()