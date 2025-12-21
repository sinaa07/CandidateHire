from pathlib import Path
from app.core.config import COLLECTIONS_ROOT


def resolve_collection_path(company_id: str, collection_id: str) -> Path:
    """Safely construct absolute path for collection root"""
    base = (COLLECTIONS_ROOT / company_id / collection_id).resolve()
    
    # Prevent path traversal attacks
    if not str(base).startswith(str(COLLECTIONS_ROOT.resolve())):
        raise ValueError("Invalid path")
    
    return base


def create_collection_dirs(base_path: Path):
    """Create collection directory structure"""
    (base_path / "input" / "raw").mkdir(parents=True, exist_ok=True)
    (base_path / "input" / "manifest").mkdir(parents=True, exist_ok=True)
    (base_path / "processed").mkdir(parents=True, exist_ok=True)
    (base_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (base_path / "outputs").mkdir(parents=True, exist_ok=True)
    (base_path / "reports").mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename"""
    unsafe_chars = ['/', '\\', '..', '\0']
    safe = filename
    for char in unsafe_chars:
        safe = safe.replace(char, '_')
    return safe.strip()


def safe_write_file(target_path: Path, file_stream):
    """Write file atomically"""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file first
    tmp_path = target_path.with_suffix('.tmp')
    with open(tmp_path, 'wb') as f:
        content = file_stream.read()
        f.write(content)
    
    # Atomic rename
    tmp_path.replace(target_path)
    file_stream.seek(0)