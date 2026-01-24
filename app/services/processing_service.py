from pathlib import Path
from datetime import datetime, UTC
import json
import logging
import os
from typing import Dict, List, Tuple, Optional
from multiprocessing import Pool, cpu_count, Manager
from app.models.enums import ResumeStatus
from app.utils.text_extraction import extract_text
from app.utils.hashing import compute_sha256
from app.utils.validation import validate_text
from app.utils.section_parser import parse_sections, sections_to_dict
from app.utils.ner.rules import extract_rule_based_entities
from app.utils.ner.spacy_ner import extract_spacy_entities, _get_spacy_model
from app.utils.ner.normalizer import normalize_entities
from app.utils.ner.base import ExtractedEntities
from app.utils.experience import compute_experience_signals
import app.core.config as config
#Phase 2 guarantees:
#- No network calls
#- No LLM usage
#- Deterministic output
#- Same input → same JSON
logger = logging.getLogger(__name__)


def _init_worker():
    """
    Initialize worker process - preload spaCy model once per process.
    This is called once when each worker process starts.
    """
    # Preload spaCy model in this worker process
    _get_spacy_model()
    logger.debug(f"Worker process {os.getpid()} initialized with spaCy model")


def _process_single_file(args: Tuple[Path, Path, Dict]) -> Dict:
    """
    Process a single resume file.
    
    This function is designed to be called by multiprocessing workers.
    
    Args:
        args: Tuple of (resume_file, processed_dir, shared_hash_registry_dict)
        
    Returns:
        Dict with keys: filename, status, reason, content_hash, duplicate_of
    """
    resume_file, processed_dir, shared_hash_registry = args
    filename = resume_file.name
    result = {
        "filename": filename,
        "status": None,
        "reason": None,
        "content_hash": None,
        "duplicate_of": None
    }
    
    try:
        # Extract text (with automatic OCR fallback for image-based PDFs)
        text = extract_text(resume_file, use_ocr_fallback=True)
        
        # Validate text
        status = validate_text(text)
        
        if status == ResumeStatus.EMPTY:
            result["status"] = ResumeStatus.EMPTY
            result["reason"] = "No extractable text (file may be image-based, corrupted, or empty)"
        elif status == ResumeStatus.OK:
            # Compute SHA-256
            content_hash = compute_sha256(text)
            result["content_hash"] = content_hash
            
            # Check for duplicates (Manager().dict() operations are already thread-safe)
            if content_hash in shared_hash_registry:
                result["status"] = ResumeStatus.DUPLICATE
                result["reason"] = f"Duplicate of {shared_hash_registry[content_hash]}"
                result["duplicate_of"] = shared_hash_registry[content_hash]
            else:
                # Register hash (atomic operation on Manager dict)
                shared_hash_registry[content_hash] = filename
                result["status"] = ResumeStatus.OK
                
                # Save processed output
                output_file = processed_dir / f"{resume_file.name}.txt"
                output_file.write_text(text, encoding='utf-8')
                
                # Extract structured intelligence (sections, entities, experience)
                try:
                    intelligence = _extract_resume_intelligence(text, filename)
                    
                    # Use output_file stem (which is resume_file.name without .txt extension)
                    base_name = output_file.stem
                    
                    # Save sections.json
                    sections_file = processed_dir / f"{base_name}_sections.json"
                    sections_file.write_text(
                        json.dumps(intelligence["sections"], indent=2),
                        encoding='utf-8'
                    )
                    
                    # Save entities.json
                    entities_file = processed_dir / f"{base_name}_entities.json"
                    entities_file.write_text(
                        json.dumps(intelligence["entities"], indent=2),
                        encoding='utf-8'
                    )
                    
                    # Save experience.json
                    experience_file = processed_dir / f"{base_name}_experience.json"
                    experience_file.write_text(
                        json.dumps(intelligence["experience"], indent=2),
                        encoding='utf-8'
                    )
                except Exception as e:
                    # Log but don't fail the entire processing
                    logger.warning(f"Failed to extract intelligence for {filename}: {e}")
                    result["status"] = ResumeStatus.FAILED
                    result["reason"] = f"Intelligence extraction failed: {str(e)}"
        else:
            result["status"] = status
            result["reason"] = "Validation failed"
            
    except KeyboardInterrupt:
        # Allow graceful cancellation
        logger.warning(f"Processing interrupted for {filename}")
        raise
    except Exception as e:
        result["status"] = ResumeStatus.FAILED
        error_msg = str(e)
        if "Unsupported file type" in error_msg:
            result["reason"] = f"Unsupported format: {resume_file.suffix} (supported: .pdf, .docx, .txt)"
        elif "Failed to extract text" in error_msg:
            result["reason"] = f"Extraction error: {error_msg}"
        elif "timeout" in error_msg.lower():
            result["reason"] = f"Processing timeout: {error_msg}"
        else:
            result["reason"] = f"Processing failed: {error_msg}"
        logger.error(f"Failed to process {filename}: {e}", exc_info=True)
    
    return result


def _extract_resume_intelligence(text: str, filename: str) -> Dict:
    """
    Extract structured intelligence from resume text.
    
    This function:
    1. Parses sections
    2. Extracts entities (rule-based + spaCy)
    3. Normalizes entities
    4. Computes experience signals
    
    Args:
        text: Resume text
        filename: Resume filename (for logging)
        
    Returns:
        Dict with sections, entities, and experience data
    """
    try:
        # 1. Parse sections (with boundaries for RAG highlighting)
        sections, boundaries = parse_sections(text, return_boundaries=True)
        sections_dict = sections_to_dict(sections, boundaries=boundaries)
        
        # 2. Extract entities (rule-based first)
        rule_entities = extract_rule_based_entities(text)
        
        # 3. Extract spaCy entities (organizations, roles, locations)
        spacy_entities = extract_spacy_entities(text)
        
        # 4. Merge entities
        entities_dict = rule_entities.to_dict()
        entities_dict["organizations"].extend(spacy_entities["organizations"])
        entities_dict["roles"].extend(spacy_entities["roles"])
        entities_dict["locations"].extend(spacy_entities["locations"])
        
        # Deduplicate lists
        entities_dict["organizations"] = sorted(list(set(entities_dict["organizations"])))
        entities_dict["roles"] = sorted(list(set(entities_dict["roles"])))
        entities_dict["locations"] = sorted(list(set(entities_dict["locations"])))
        
        # 5. Normalize entities
        entities_dict = normalize_entities(entities_dict)
        
        # 6. Reconstruct ExtractedEntities for experience calculation
        normalized_entities = ExtractedEntities.from_dict(entities_dict)
        
        # 7. Compute experience signals
        experience_signals = compute_experience_signals(normalized_entities)
        
        return {
            "sections": sections_dict,
            "entities": entities_dict,
            "experience": experience_signals
        }
    except Exception as e:
        logger.warning(f"Failed to extract intelligence from {filename}: {e}")
        # Return empty structure on failure
        return {
            "sections": {
                "summary": "",
                "experience": "",
                "skills": "",
                "education": "",
                "projects": "",
                "other": ""
            },
            "entities": {
                "skills": {},
                "roles": [],
                "organizations": [],
                "education": {},
                "experience": {},
                "locations": []
            },
            "experience": {
                "experience_depth": 0.0,
                "stability": 0.0,
                "years_min": None,
                "years_max": None,
                "role_count": 0,
                "earliest_date": None,
                "latest_date": None
            }
        }


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
    
    # 3. Initialize shared hash registry for duplicate detection
    # Use Manager for thread-safe shared dictionary across processes
    manager = Manager()
    shared_hash_registry = manager.dict()
    
    # 4. Prepare file processing arguments
    file_args = [(resume_file, processed_dir, shared_hash_registry) for resume_file in resume_files]
    
    # 5. Process files in parallel using multiprocessing (or sequential for small batches)
    # For very few files, sequential processing avoids multiprocessing overhead
    use_multiprocessing = len(resume_files) > 2
    
    validation_files = []
    duplicates = []
    stats = {
        "total_files": len(resume_files),
        "ok": 0,
        "failed": 0,
        "empty": 0,
        "duplicate": 0
    }
    
    try:
        if use_multiprocessing:
            # Determine optimal worker count (balance CPU cores vs memory)
            num_workers = min(8, max(2, cpu_count() - 1))  # Leave 1 core free, max 8 workers
            logger.info(f"Processing {len(resume_files)} files with {num_workers} worker processes")
            
            # Use multiprocessing Pool with initializer to preload spaCy model per worker
            with Pool(processes=num_workers, initializer=_init_worker) as pool:
                # Process files in parallel
                results = pool.map(_process_single_file, file_args)
        else:
            # Sequential processing for small batches (avoids multiprocessing overhead)
            logger.info(f"Processing {len(resume_files)} files sequentially (small batch)")
            # Preload spaCy model in main process
            _get_spacy_model()
            results = [_process_single_file(args) for args in file_args]
        
        # Process results
        for result in results:
            filename = result["filename"]
            status = result["status"]
            reason = result["reason"]
            
            # Record validation result
            validation_files.append({
                "filename": filename,
                "status": status.value if status else None,
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
                duplicates.append({
                    "filename": filename,
                    "duplicate_of": result["duplicate_of"]
                })
        
        logger.info(f"Processing completed: {stats['ok']} OK, {stats['failed']} failed, "
                   f"{stats['empty']} empty, {stats['duplicate']} duplicates")
    
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        raise
    except Exception as e:
        logger.error(f"Multiprocessing error: {e}", exc_info=True)
        raise
    
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