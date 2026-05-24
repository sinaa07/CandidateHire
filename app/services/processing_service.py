from pathlib import Path
from datetime import datetime, UTC
import json
import logging
import os
from multiprocessing import Pool, cpu_count, Manager
from app.models.enums import ResumeStatus
from app.utils.ner.spacy_ner import _get_spacy_model
from app.utils.latency_tracker import LatencyRecorder, save_latency_report
from app.workers.resume_worker import process_resume_file
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
    latency_recorder = LatencyRecorder()
    latency_report_path = None
    
    try:
        if use_multiprocessing:
            # Determine optimal worker count (balance CPU cores vs memory)
            num_workers = min(8, max(2, cpu_count() - 1))  # Leave 1 core free, max 8 workers
            logger.info(f"Processing {len(resume_files)} files with {num_workers} worker processes")
            
            # Use multiprocessing Pool with initializer to preload spaCy model per worker
            with Pool(processes=num_workers, initializer=_init_worker) as pool:
                # Process files in parallel
                results = pool.map(process_resume_file, file_args)
        else:
            # Sequential processing for small batches (avoids multiprocessing overhead)
            logger.info(f"Processing {len(resume_files)} files sequentially (small batch)")
            # Preload spaCy model in main process
            _get_spacy_model()
            results = [process_resume_file(args) for args in file_args]
        
        # Merge per-file latency samples
        for result in results:
            samples = result.get("latency_samples")
            if samples:
                latency_recorder.merge_samples(samples)
        
        # Process results
        for result in results:
            filename = result["filename"]
            status = result["status"]
            reason = result["reason"]
            
            # Record validation result
            entry = {
                "filename": filename,
                "status": status.value if status else None,
                "reason": reason,
            }
            extraction = result.get("extraction")
            if extraction:
                entry["extraction_method"] = extraction.get("method")
                entry["extraction_state"] = extraction.get("state")
                entry["ocr_triggered"] = extraction.get("ocr_triggered")
                entry["char_count"] = extraction.get("char_count")
                entry["latency_ms"] = extraction.get("latency_ms")
            validation_files.append(entry)
            
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
    
    # 5b. Persist latency report (p50 / p95 / p99 per stage)
    if latency_recorder.to_samples_dict():
        latency_report_path = save_latency_report(
            reports_dir,
            latency_recorder,
            label="phase2_processing",
        )
        logger.info(f"Latency report saved: {latency_report_path}")
    
    # 6. Update collection_meta.json
    meta_file = collection_root / "collection_meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    meta.update({
        "processing_status": "completed",
        "processed_at": datetime.now(UTC).isoformat()
    })
    meta_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    
    logger.info("Phase-2 processing completed")
    
    reports_generated = [
        "validation_report.json",
        "duplicate_report.json",
    ]
    if latency_report_path and latency_report_path.exists():
        reports_generated.append("latency_report.json")
    
    response = {
        "status": "completed",
        "stats": stats,
        "reports_generated": reports_generated,
    }
    if latency_report_path and latency_report_path.exists():
        response["latency"] = json.loads(latency_report_path.read_text(encoding="utf-8"))
    return response