from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import logging
from app.utils.paths import get_collection_root, assert_collection_exists
from app.utils.io_reports import read_json_file, get_report_paths
from app.core.errors import to_http_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["reports"])

@router.get("/{collection_id}/report")
async def get_collection_report(
    collection_id: str,
    company_id: str = Query(..., description="Company identifier"),
    include_results: bool = Query(False, description="Include full ranking results")
) -> dict:
    """
    Return aggregated reports for a collection.
    
    Args:
        collection_id: Collection identifier
        company_id: Company identifier
        include_results: Whether to include full ranking results
        
    Returns:
        Aggregated report dictionary
        
    Raises:
        HTTPException: 404 if collection not found
    """
    try:
        # Resolve collection root
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        # Get report paths
        paths = get_report_paths(collection_root)
        
        # Build response
        response = {
            "collection_id": collection_id,
            "company_id": company_id,
            "meta": None,
            "phase2": {
                "validation_report": None,
                "duplicate_report": None
            },
            "phase3": {
                "ranking_summary": None
            }
        }
        
        # Read meta if exists
        try:
            response["meta"] = read_json_file(paths["meta"])
        except ValueError:
            pass
        
        # Read Phase 2 reports if exist
        try:
            response["phase2"]["validation_report"] = read_json_file(paths["validation"])
        except ValueError:
            pass
        
        try:
            response["phase2"]["duplicate_report"] = read_json_file(paths["duplicates"])
        except ValueError:
            pass
        
        # Read Phase 3 reports if exist
        try:
            response["phase3"]["ranking_summary"] = read_json_file(paths["ranking_summary"])
        except ValueError:
            pass
        
        # Include full results if requested
        if include_results:
            try:
                response["phase3"]["ranking_results"] = read_json_file(paths["ranking_json"])
            except ValueError:
                pass
        
        return response
        
    except Exception as exc:
        raise to_http_error(exc)

@router.get("/{collection_id}/outputs")
async def get_collection_outputs(
    collection_id: str,
    company_id: str = Query(..., description="Company identifier")
) -> dict:
    """
    Return file availability for collection outputs.
    
    Args:
        collection_id: Collection identifier
        company_id: Company identifier
        
    Returns:
        Dictionary showing output file availability
        
    Raises:
        HTTPException: 404 if collection not found
    """
    try:
        # Resolve collection root
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        # Get report paths
        paths = get_report_paths(collection_root)
        
        # Check file availability
        outputs = {
            "ranking_results.json": paths["ranking_json"].exists(),
            "ranking_results.csv": paths["ranking_csv"].exists()
        }
        
        return {"outputs": outputs}
        
    except Exception as exc:
        raise to_http_error(exc)

@router.get("/{collection_id}/entities/{filename}")
async def get_resume_entities(
    collection_id: str,
    filename: str,
    company_id: str = Query(..., description="Company identifier")
) -> dict:
    """
    Get NER entities for a specific resume.
    
    Args:
        collection_id: Collection identifier
        filename: Resume filename (e.g., "resume.pdf.txt" or "resume.pdf")
        company_id: Company identifier
        
    Returns:
        Dictionary with entities data
        
    Raises:
        HTTPException: 404 if collection or entities file not found
    """
    try:
        # Resolve collection root
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        # Get processed directory
        processed_dir = collection_root / "processed"
        if not processed_dir.exists():
            raise ValueError("Processed directory not found")
        
        # Handle filename: could be "resume.pdf.txt" (from ranking) or "resume.pdf" (original)
        # The entities file is named as "{original_filename}_entities.json"
        # Processing saves files as "{original_filename}.txt", so we need to:
        # 1. If filename ends with .txt, remove it to get original name
        # 2. Use that as base for entities file
        
        # URL decode the filename in case it's encoded
        import urllib.parse
        filename = urllib.parse.unquote(filename)
        
        logger.debug(f"Looking for entities for filename: {filename}")
        
        filename_path = Path(filename)
        
        # If filename ends with .txt, remove it (it's the processed .txt file)
        if filename_path.suffix == ".txt":
            base_name = filename_path.stem  # This removes .txt, leaving original name (e.g., "resume.pdf")
        else:
            # It's the original filename, use as is
            base_name = filename_path.stem
        
        logger.debug(f"Extracted base name: {base_name}")
        
        # Try to find entities file
        entities_file = processed_dir / f"{base_name}_entities.json"
        logger.debug(f"Looking for entities file: {entities_file}")
        
        # If not found, try alternative patterns
        if not entities_file.exists():
            # Try with the full filename stem (in case there are multiple dots)
            alt_file = processed_dir / f"{filename_path.stem}_entities.json"
            if alt_file.exists():
                logger.debug(f"Found alternative entities file: {alt_file}")
                entities_file = alt_file
            else:
                # Try searching for any entities file that matches
                # List all entities files
                available_entities = list(processed_dir.glob("*_entities.json"))
                logger.debug(f"Found {len(available_entities)} total entities files")
                
                # Try to find a match by comparing base names
                for entity_file in available_entities:
                    entity_base = entity_file.stem.replace("_entities", "")
                    # Check if the base name matches (handling different extensions)
                    if entity_base == base_name or entity_base == filename_path.stem:
                        logger.debug(f"Matched entities file: {entity_file}")
                        entities_file = entity_file
                        break
                
                # If still not found, provide helpful error
                if not entities_file.exists():
                    available_names = [f.stem.replace("_entities", "") for f in available_entities[:10]]
                    error_msg = (
                        f"Entities file not found for filename '{filename}'. "
                        f"Tried base name: '{base_name}'. "
                    )
                    if available_entities:
                        error_msg += f"Available entities files (first 10): {available_names}"
                    else:
                        error_msg += (
                            "No entities files found in processed directory. "
                            "This usually means processing failed or entities extraction was not completed. "
                            "Please re-run processing (Phase 2) to generate entities files."
                        )
                    logger.warning(error_msg)
                    raise ValueError(error_msg)
        
        # Read entities JSON
        entities_data = read_json_file(entities_file)
        
        return {
            "filename": filename,
            "entities": entities_data
        }
        
    except Exception as exc:
        raise to_http_error(exc)
