from fastapi import APIRouter, HTTPException, Query
from app.utils.paths import get_collection_root, assert_collection_exists
from app.utils.io_reports import read_json_file, get_report_paths
from app.core.errors import to_http_error

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
