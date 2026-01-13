"""RAG API endpoints."""
import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import Dict
from asyncio import Queue
from app.models.rag_schemas import (
    RAGQueryRequest, RAGStatusResponse, RAGQueryResponse,
    RAGInitializeRequest, RAGInitializeResponse
)
from app.utils.paths import get_collection_root, assert_collection_exists
from app.services.rag_service import (
    build_rag_index, get_rag_status, process_rag_query
)
from app.core.errors import to_http_error

router = APIRouter(prefix="/collections", tags=["rag"])

# In-memory task storage (for production, use Redis or database)
_active_tasks: Dict[str, Dict] = {}


async def _run_rag_query(
    task_id: str,
    company_id: str,
    collection_id: str,
    query: str,
    top_k: int,
    filters: dict,
    include_context: bool,
    use_ranking: bool,
    queue: Queue
) -> None:
    """Background task for RAG query processing."""
    try:
        _active_tasks[task_id]["status"] = "processing"
        async for chunk in process_rag_query(
            company_id=company_id,
            collection_id=collection_id,
            query=query,
            top_k=top_k,
            filters=filters,
            include_context=include_context,
            use_ranking=use_ranking
        ):
            await queue.put(chunk)
        
        await queue.put(None)  # Signal completion
        _active_tasks[task_id]["status"] = "completed"
    except Exception as e:
        await queue.put(None)  # Signal error
        _active_tasks[task_id]["status"] = "failed"
        _active_tasks[task_id]["error"] = str(e)


@router.post("/{collection_id}/rag/initialize", response_model=RAGInitializeResponse)
async def initialize_rag(
    collection_id: str,
    request: RAGInitializeRequest
) -> RAGInitializeResponse:
    """
    Manually trigger RAG index build.
    
    Args:
        collection_id: Collection identifier
        request: Request with company_id
        
    Returns:
        Initialization result
    """
    try:
        collection_root = get_collection_root(request.company_id, collection_id)
        assert_collection_exists(collection_root)
        
        result = build_rag_index(request.company_id, collection_id)
        
        return RAGInitializeResponse(
            status="completed",
            collection_id=collection_id,
            details=result
        )
    except Exception as exc:
        raise to_http_error(exc)


@router.get("/{collection_id}/rag/status", response_model=RAGStatusResponse)
async def get_rag_status_endpoint(
    collection_id: str,
    company_id: str = Query(..., description="Company identifier")
) -> RAGStatusResponse:
    """
    Get RAG status for a collection.
    
    Args:
        collection_id: Collection identifier
        company_id: Company identifier (query parameter)
        
    Returns:
        RAG status information
    """
    try:
        if not company_id:
            raise ValueError("company_id query parameter is required")
        
        status = get_rag_status(company_id, collection_id)
        
        return RAGStatusResponse(**status)
    except Exception as exc:
        raise to_http_error(exc)


@router.post("/{collection_id}/rag/query", response_model=RAGQueryResponse)
async def query_rag(
    collection_id: str,
    request: RAGQueryRequest,
    background_tasks: BackgroundTasks
) -> RAGQueryResponse:
    """
    Submit RAG query (async, returns task_id).
    
    Args:
        collection_id: Collection identifier
        request: RAG query request
        background_tasks: FastAPI background tasks
        
    Returns:
        Task ID for streaming endpoint
    """
    try:
        # Validate collection exists
        collection_root = get_collection_root(request.company_id, collection_id)
        assert_collection_exists(collection_root)
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Prepare filters
        filters_dict = {}
        if request.filters:
            filters_dict = {
                "use_ranking": request.filters.use_ranking,
                "min_rank_position": request.filters.min_rank_position,
                "max_rank_position": request.filters.max_rank_position,
                "min_ranking_score": request.filters.min_ranking_score,
                "required_skills": request.filters.required_skills or []
            }
        
        # Initialize task with queue
        queue: Queue = Queue()
        _active_tasks[task_id] = {
            "status": "queued",
            "company_id": request.company_id,
            "collection_id": collection_id,
            "queue": queue
        }
        
        # Queue background task
        background_tasks.add_task(
            _run_rag_query,
            task_id=task_id,
            company_id=request.company_id,
            collection_id=collection_id,
            query=request.query,
            top_k=request.top_k,
            filters=filters_dict,
            include_context=request.include_context,
            use_ranking=filters_dict.get("use_ranking", True),
            queue=queue
        )
        
        return RAGQueryResponse(task_id=task_id, status="queued")
        
    except Exception as exc:
        raise to_http_error(exc)


@router.get("/rag/stream/{task_id}")
async def stream_rag_response(task_id: str):
    """
    SSE endpoint for streaming RAG response.
    
    Args:
        task_id: Task identifier from query endpoint
        
    Returns:
        Server-Sent Events stream
    """
    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    async def event_generator():
        """Generate SSE events with real-time streaming."""
        task = _active_tasks[task_id]
        queue: Queue = task.get("queue")
        
        if not queue:
            yield f"data: Error: Task queue not found\n\n"
            return
        
        # Wait for task to start (max 10 seconds)
        wait_count = 0
        while task["status"] == "queued" and wait_count < 20:
            await asyncio.sleep(0.5)
            wait_count += 1
        
        if task["status"] == "queued":
            yield f"data: Error: Task timeout\n\n"
            return
        
        # Stream chunks in real-time
        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=60.0)
                if chunk is None:
                    # Completion signal
                    break
                # Send chunk as SSE data
                yield f"data: {chunk}\n\n"
            except asyncio.TimeoutError:
                yield f"data: Error: Stream timeout\n\n"
                break
            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"
                break
        
        # Check final status
        if task.get("status") == "failed":
            error = task.get("error", "Unknown error")
            yield f"data: Error: {error}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
