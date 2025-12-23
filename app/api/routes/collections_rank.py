from fastapi import APIRouter, HTTPException
from app.models.api_schemas import RankRequest, StandardResponse
from app.utils.paths import get_collection_root, assert_collection_exists
from app.services.ranking_service import rank_collection
from app.core.errors import to_http_error

router = APIRouter(prefix="/collections", tags=["ranking"])

@router.post("/{collection_id}/rank")
async def rank_collection_endpoint(
    collection_id: str,
    request: RankRequest
) -> StandardResponse:
    """
    Trigger Phase 3 ranking for a collection.
    
    Args:
        collection_id: Collection identifier
        request: Rank request with company_id, jd_text, and optional top_k
        
    Returns:
        Ranking summary
        
    Raises:
        HTTPException: 404 if collection not found, 400 on validation error
    """
    try:
        # 1. Resolve collection root
        collection_root = get_collection_root(request.company_id, collection_id)
        
        # 2. Assert collection exists
        assert_collection_exists(collection_root)
        
        # 3. Validate inputs (done by Pydantic)
        
        # 4. Guard: ensure Phase 2 completed
        processed_dir = collection_root / "processed"
        if not processed_dir.exists() or not list(processed_dir.glob("*.txt")):
            raise ValueError("Run processing first - no processed resumes found")
        
        # 5. Call ranking service
        result = rank_collection(
            request.company_id,
            collection_id,
            request.jd_text,
            request.top_k
        )
        
        # 6. Return ranking summary
        return StandardResponse(
            status="completed",
            collection_id=collection_id,
            details=result
        )
        
    except Exception as exc:
        raise to_http_error(exc)

