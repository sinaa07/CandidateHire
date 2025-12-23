import json
import uuid
import shutil
from datetime import datetime, UTC
from pathlib import Path
from app.utils.filesystem import (
    resolve_collection_path,
    create_collection_dirs,
    safe_write_file
)
from app.utils.zip_utils import is_valid_zip, extract_zip_safe
from app.core.logger import logger


def create_collection(company_id: str, zip_file) -> dict:
    """
    Create a new isolated collection for a company.
    
    Execution order (STRICT):
    1. Generate unique collection_id
    2. Resolve base path
    3. Create directory structure
    4. Persist ZIP file
    5. Validate ZIP
    6. Extract ZIP contents
    7. Create metadata
    8. Return response
    """
    
    # 1. Generate unique collection_id
    collection_id = str(uuid.uuid4())
    
    # 2. Resolve base path
    base_path = resolve_collection_path(company_id, collection_id)
    
    # 3. Create directory structure
    create_collection_dirs(base_path)
    logger.info(f"Created collection dirs: {base_path}")
    
    # 4. Persist ZIP file
    zip_path = base_path / "input" / "resumes.zip"
    safe_write_file(zip_path, zip_file.file)
    logger.info(f"Saved ZIP: {zip_path}")
    
    # 5. Validate ZIP
    if not is_valid_zip(zip_path):
        shutil.rmtree(base_path, ignore_errors=True)
        raise ValueError("Invalid or corrupted ZIP file")
    
    # 6. Extract ZIP contents
    raw_dir = base_path / "input" / "raw"
    extract_zip_safe(zip_path, raw_dir)
    
    # Count extracted resumes
    resume_count = len(list(raw_dir.iterdir()))
    
    if resume_count == 0:
        shutil.rmtree(base_path, ignore_errors=True)
        raise ValueError("ZIP contained no valid files")

    logger.info(f"Extracted ZIP to: {raw_dir}")
    
    # 7. Create metadata
    metadata = {
        "collection_id": collection_id,
        "company_id": company_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "uploaded",
        "format": "zip_only",
        "resume_count": resume_count
    }
    
    metadata_path = base_path / "collection_meta.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Created metadata: {metadata_path}")
    
    # 8. Return response
    return {
        "collection_id": collection_id,
        "status": "uploaded"
    }