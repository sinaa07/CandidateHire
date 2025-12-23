from pathlib import Path
import json

def read_json_file(path: Path) -> dict | list:
    """
    Read JSON file safely.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON content
        
    Raises:
        ValueError: If file not found or invalid JSON
    """
    if not path.exists():
        raise ValueError("Report not found")
    
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON report")

def read_text_file(path: Path) -> str:
    """
    Read text file safely.
    
    Args:
        path: Path to text file
        
    Returns:
        File content
        
    Raises:
        ValueError: If file not found
    """
    if not path.exists():
        raise ValueError("Report not found")
    
    return path.read_text(encoding='utf-8')

def get_report_paths(collection_root: Path) -> dict:
    """
    Get dictionary of expected report paths.
    
    Args:
        collection_root: Collection root directory
        
    Returns:
        Dictionary mapping report names to paths
    """
    return {
        "validation": collection_root / "reports" / "validation_report.json",
        "duplicates": collection_root / "reports" / "duplicate_report.json",
        "ranking_summary": collection_root / "reports" / "ranking_summary.json",
        "ranking_json": collection_root / "outputs" / "ranking_results.json",
        "ranking_csv": collection_root / "outputs" / "ranking_results.csv",
        "meta": collection_root / "collection_meta.json"
    }
