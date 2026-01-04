from pathlib import Path
from datetime import datetime, UTC
import json
import logging
from typing import Dict, List
from app.models.enums import ResumeStatus
from app.utils.text_extraction import extract_text
from app.utils.hashing import compute_sha256
from app.utils.validation import validate_text
import app.core.config as config

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
    collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
    input_dir = collection_root / "input" / "raw"
    processed_dir = collection_root / "processed"
    reports_dir = collection_root / "reports"
    
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Read files from input/raw/ (recursively to handle subdirectories)
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        raise ValueError(f"Input directory not found: {input_dir}")
    
    resume_files = list(input_dir.rglob("*"))
    # Filter out system/metadata files (macOS resource forks, .DS_Store, Thumbs.db, etc.)
    resume_files = [
        f for f in resume_files 
        if f.is_file() 
        and f.suffix.lower() in ['.pdf', '.docx', '.txt']
        and not f.name.startswith('._')  # macOS resource fork files
        and f.name != '.DS_Store'  # macOS metadata
        and f.name != 'Thumbs.db'  # Windows metadata
        and not f.name.startswith('~$')  # Windows temp files
    ]
    resume_files = sorted(resume_files)
    
    # Log file type distribution for debugging
    file_types = {}
    for f in resume_files:
        ext = f.suffix.lower()
        file_types[ext] = file_types.get(ext, 0) + 1
    
    logger.info(f"Found {len(resume_files)} resume files in {input_dir}")
    logger.info(f"File type distribution: {file_types}")
    
    # Check for unsupported file types (especially .doc files)
    all_files = [f for f in input_dir.rglob("*") if f.is_file()]
    unsupported = [f for f in all_files if f.suffix.lower() not in ['.pdf', '.docx', '.txt', '.zip']]
    if unsupported:
        unsupported_types = {}
        for f in unsupported:
            ext = f.suffix.lower() or '(no extension)'
            unsupported_types[ext] = unsupported_types.get(ext, 0) + 1
        logger.warning(f"Found {len(unsupported)} unsupported files (types: {unsupported_types})")
        if '.doc' in unsupported_types:
            logger.warning(f"Note: {unsupported_types['.doc']} .doc files found. Only .docx (newer Word format) is supported.")
    
    if len(resume_files) == 0:
        logger.warning(f"No resume files found in {input_dir}. All files: {list(input_dir.rglob('*'))}")
    
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
                reason = "No extractable text (file may be image-based, corrupted, or empty)"
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
            # Include more detailed error information
            error_msg = str(e)
            if "Unsupported file type" in error_msg:
                reason = f"Unsupported format: {resume_file.suffix} (supported: .pdf, .docx, .txt)"
            elif "Failed to extract text" in error_msg:
                reason = f"Extraction error: {error_msg}"
            else:
                reason = f"Processing failed: {error_msg}"
            logger.error(f"Failed to process {filename}: {e}", exc_info=True)
        
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
        "processed_at": datetime.now(UTC).isoformat()
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