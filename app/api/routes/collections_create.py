from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import uuid
import zipfile
import shutil
import app.core.config as config
from app.core.errors import to_http_error
import json
from datetime import datetime, UTC
from fastapi.responses import JSONResponse

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
        
        # Extract ZIP (skip macOS resource fork files and other metadata)
        try:
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                skipped_files = []
                extracted_count = 0
                for member in zf.namelist():
                    # Skip macOS resource fork files (._*), .DS_Store, and other metadata
                    if (member.startswith('._') or 
                        member.endswith('/.DS_Store') or 
                        member == '.DS_Store' or
                        member == 'Thumbs.db' or
                        member.startswith('~$')):
                        skipped_files.append(member)
                        continue
                    # Skip directory entries
                    if member.endswith('/'):
                        continue
                    # Extract file
                    try:
                        zf.extract(member, raw_dir)
                        extracted_count += 1
                    except Exception as e:
                        # Log but continue with other files
                        print(f"Warning: Failed to extract {member}: {e}")
                        skipped_files.append(member)
                
                if skipped_files:
                    print(f"Note: Skipped {len(skipped_files)} metadata/system files (e.g., macOS resource forks)")
        except zipfile.BadZipFile:
            # Clean up and raise error
            shutil.rmtree(collection_root)
            raise ValueError("Invalid ZIP file")
        finally:
            # Remove temp ZIP
            if temp_zip.exists():
                temp_zip.unlink()
        
        # Check if ZIP was empty (after filtering)
        valid_files = [f for f in raw_dir.rglob("*") 
                      if f.is_file() 
                      and not f.name.startswith('._')
                      and f.name != '.DS_Store']
        if not valid_files:
            shutil.rmtree(collection_root)
            raise ValueError("ZIP file is empty or contains no valid resume files")
        
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