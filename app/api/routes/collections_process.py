from fastapi import APIRouter, HTTPException
from app.models.api_schemas import ProcessRequest, StandardResponse
from app.utils.paths import get_collection_root, assert_collection_exists
from app.services.processing_service import process_collection
from app.core.errors import to_http_error
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

router = APIRouter(prefix="/collections", tags=["processing"])

# Thread pool for CPU-intensive processing with timeout protection
executor = ThreadPoolExecutor(max_workers=1)

@router.post("/{collection_id}/process")
async def process_collection_endpoint(
    collection_id: str,
    request: ProcessRequest
) -> StandardResponse:
    """
    Trigger Phase 2 processing for an existing collection.
    
    Args:
        collection_id: Collection identifier
        request: Process request with company_id
        
    Returns:
        Processing summary
        
    Raises:
        HTTPException: 404 if collection not found, 400 on validation error
    """
    try:
        # 1. Resolve collection root
        collection_root = get_collection_root(request.company_id, collection_id)
        
        # 2. Assert collection exists
        assert_collection_exists(collection_root)
        
        # Check for raw files
        input_dir = collection_root / "input" / "raw"
        if not input_dir.exists() or not list(input_dir.glob("*")):
            raise ValueError("No resume files found in collection")
        
        # 3. Run processing in executor with timeout (30 minutes max)
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, process_collection, request.company_id, collection_id),
                timeout=1800.0  # 30 minutes
            )
        except asyncio.TimeoutError:
            raise ValueError("Processing timed out after 30 minutes. Please try again or check for problematic files.")
        
        # 4. Return processing summary
        return StandardResponse(
            status="completed",
            collection_id=collection_id,
            details=result
        )
        
    except Exception as exc:
        raise to_http_error(exc)

