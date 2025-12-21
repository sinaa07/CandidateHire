from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Dict, List
from app.models.enums import ResumeStatus
from app.utils.text_extraction import extract_text
from app.utils.hashing import compute_sha256
from app.utils.validation import validate_text
from app.core.config import COLLECTIONS_ROOT

logger = logging.getLogger(__name__)

def process_collection(company_id: str, collection_id: str) -> dict:
    """
    Core Phase-2 orchestration logic.
    
    Processes all resumes in a collection:
    - Extracts text
    - Validates content
    - Detects duplicates
    - Generates reports
    
    Args:
        company_id: Company identifier
        collection_id: Collection identifier
        
    Returns:
        dict: Processing summary
    """
    logger.info(f"Processing collection {collection_id}")
    
    # 1. Resolve collection paths
    collection_root = COLLECTIONS_ROOT / company_id / collection_id
    input_dir = collection_root / "input" / "raw"
    processed_dir = collection_root / "processed"
    reports_dir = collection_root / "reports"
    
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Read files from input/raw/
    resume_files = list(input_dir.glob("*"))
    resume_files = [f for f in resume_files if f.is_file() and f.suffix.lower() in ['.pdf', '.docx', '.txt']]
    resume_files = sorted(resume_files)
    
    # 3. Initialize hash registry
    hash_registry = {}
    
    # 4. Process each resume file
    validation_files = []
    duplicates = []
    stats = {
        "total_files": len(resume_files),
        "ok": 0,
        "failed": 0,
        "empty": 0,
        "duplicate": 0
    }
    
    for resume_file in resume_files:
        filename = resume_file.name
        status = None
        reason = None
        
        try:
            # Extract text
            text = extract_text(resume_file)
            
            # Validate text
            status = validate_text(text)
            
            if status == ResumeStatus.EMPTY:
                reason = "No extractable text"
            elif status == ResumeStatus.OK:
                # Compute SHA-256
                content_hash = compute_sha256(text)
                
                # Detect duplicates
                if content_hash in hash_registry:
                    status = ResumeStatus.DUPLICATE
                    reason = f"Duplicate of {hash_registry[content_hash]}"
                    duplicates.append({
                        "filename": filename,
                        "duplicate_of": hash_registry[content_hash]
                    })
                else:
                    # Register hash
                    hash_registry[content_hash] = filename
                    
                    # Save processed output (use full filename to prevent overwrites)
                    output_file = processed_dir / f"{resume_file.name}.txt"
                    output_file.write_text(text, encoding='utf-8')
            
        except Exception as e:
            status = ResumeStatus.FAILED
            reason = "Text extraction failed"
            logger.error(f"Failed to process {filename}: {e}")
        
        # Record result
        validation_files.append({
            "filename": filename,
            "status": status.value,
            "reason": reason
        })
        
        # Update stats
        if status == ResumeStatus.OK:
            stats["ok"] += 1
        elif status == ResumeStatus.EMPTY:
            stats["empty"] += 1
        elif status == ResumeStatus.FAILED:
            stats["failed"] += 1
        elif status == ResumeStatus.DUPLICATE:
            stats["duplicate"] += 1
    
    # 5. Generate reports
    validation_report = {
        **stats,
        "files": validation_files
    }
    
    duplicate_report = {
        "duplicates": duplicates
    }
    
    (reports_dir / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2),
        encoding='utf-8'
    )
    
    (reports_dir / "duplicate_report.json").write_text(
        json.dumps(duplicate_report, indent=2),
        encoding='utf-8'
    )
    
    # 6. Update collection_meta.json
    meta_file = collection_root / "collection_meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    meta.update({
        "processing_status": "completed",
        "processed_at": datetime.utcnow().isoformat()
    })
    meta_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    
    logger.info("Phase-2 processing completed")
    
    return {
        "status": "completed",
        "stats": stats,
        "reports_generated": [
            "validation_report.json",
            "duplicate_report.json"
        ]
    }