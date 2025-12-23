from pathlib import Path
import app.core.config as config

def get_collection_root(company_id: str, collection_id: str) -> Path:
    """
    Resolve collection root path safely.
    
    Args:
        company_id: Company identifier
        collection_id: Collection identifier
        
    Returns:
        Resolved path to collection root
        
    Raises:
        ValueError: If path traversal detected
    """
    collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
    
    # Validate containment (prevent path traversal)
    try:
        resolved = collection_root.resolve()
        resolved.relative_to(config.COLLECTIONS_ROOT.resolve())
        return resolved
    except ValueError:
        raise ValueError("Collection path invalid")

def assert_collection_exists(collection_root: Path) -> None:
    """
    Assert that collection exists.
    
    Args:
        collection_root: Collection root path
        
    Raises:
        ValueError: If collection not found
    """
    if not collection_root.exists():
        raise ValueError("Collection not found")