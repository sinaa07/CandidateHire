import zipfile
from pathlib import Path
from app.core.logger import logger


def is_valid_zip(zip_path: Path) -> bool:
    """Verify ZIP integrity"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            return zf.testzip() is None
    except (zipfile.BadZipFile, Exception):
        return False


def extract_zip_safe(zip_path: Path, target_dir: Path):
    """Extract ZIP contents safely, preventing zip-slip attacks"""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            # Skip directory entries
            if member.endswith('/'):
                continue
            
            # Sanitize member name to prevent nested paths
            safe_name = member.replace("/", "_").replace("\\", "_")
            member_path = target_dir / safe_name
            
            # Prevent path traversal
            if not member_path.resolve().is_relative_to(target_dir.resolve()):
                logger.warning(f"Skipping unsafe path: {member}")
                continue
            
            try:
                # Extract file
                member_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(member_path, 'wb') as target:
                    target.write(source.read())
            except Exception as e:
                logger.warning(f"Failed to extract {member}: {e}")
                continue