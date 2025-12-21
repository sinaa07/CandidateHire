from pathlib import Path

def save_jd_text(collection_root: Path, jd_text: str) -> Path:
    """
    Writes JD text to collection_root/input/jd.txt
    
    Args:
        collection_root: Collection root directory
        jd_text: Job description text
        
    Returns:
        Path to jd.txt
    """
    input_dir = collection_root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    jd_file = input_dir / "jd.txt"
    jd_file.write_text(jd_text.strip(), encoding='utf-8')
    
    return jd_file

def load_jd_text(collection_root: Path) -> str:
    """
    Reads collection_root/input/jd.txt
    
    Args:
        collection_root: Collection root directory
        
    Returns:
        JD text content (stripped)
        
    Raises:
        ValueError: If JD file not found
    """
    jd_file = collection_root / "input" / "jd.txt"
    
    if not jd_file.exists():
        raise ValueError("JD not found")
    
    return jd_file.read_text(encoding='utf-8').strip()