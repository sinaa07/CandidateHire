from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import uuid
import zipfile
import shutil
import app.core.config as config
from app.core.errors import to_http_error
import json
from datetime import datetime, UTC

router = APIRouter(prefix="/collections", tags=["collections"])

@router.post("/create")
async def create_collection(
    company_id: str = Form(...),
    zip_file: UploadFile = File(...)
):
    """Create a new collection by uploading a ZIP file of resumes."""
    try:
        # Generate collection ID
        collection_id = str(uuid.uuid4())
        
        # Get collection root - DON'T use get_collection_root, use config.COLLECTIONS_ROOT directly
        collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
        collection_root.mkdir(parents=True, exist_ok=True)
        
        # Create directories
        raw_dir = collection_root / "input" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded ZIP temporarily
        temp_zip = collection_root / "temp.zip"
        with open(temp_zip, 'wb') as f:
            content = await zip_file.read()
            f.write(content)
        
        # Extract ZIP
        try:
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                # Extract all files
                zf.extractall(raw_dir)
        except zipfile.BadZipFile:
            # Clean up and raise error
            shutil.rmtree(collection_root)
            raise ValueError("Invalid ZIP file")
        finally:
            # Remove temp ZIP
            if temp_zip.exists():
                temp_zip.unlink()
        
        # Check if ZIP was empty
        if not list(raw_dir.glob("*")):
            shutil.rmtree(collection_root)
            raise ValueError("ZIP file is empty")
        
        # Create collection metadata
        meta = {
            "collection_id": collection_id,
            "company_id": company_id,
            "created_at": datetime.now(UTC).isoformat(),
            "upload_status": "uploaded"
        }
        
        meta_file = collection_root / "collection_meta.json"
        meta_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
        
        return {
            "status": "uploaded",
            "collection_id": collection_id,
            "company_id": company_id
        }
        
    except Exception as exc:
        raise to_http_error(exc)