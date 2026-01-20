from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.api.routes import collections_create, collections_process, collections_rank, collections_report
from app.api.routes import collections_rank_file, collections_rag, collections_evaluate
import asyncio
app = FastAPI(
    title="CandidateHire API",
    description="Resume ranking and processing system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(collections_rank_file.router)
app.include_router(collections_create.router)      # Phase 1 - create collection
app.include_router(collections_process.router)     # Phase 2 - process
app.include_router(collections_rank.router)        # Phase 3 - rank
app.include_router(collections_report.router)      # Phase 4 - reports
app.include_router(collections_rag.router)         # RAG - retrieval-augmented generation
app.include_router(collections_evaluate.router)    # RAG evaluation

@app.get("/")
async def root():
    return {
        "service": "CandidateHire API",
        "version": "1.0.0",
        "endpoints": {
            "create": "/collections/create (POST)",
            "process": "/collections/{id}/process (POST)",
            "rank": "/collections/{id}/rank (POST)",
            "report": "/collections/{id}/report (GET)",
            "outputs": "/collections/{id}/outputs (GET)",
            "rag": "/collections/{id}/rag/query (POST)",
            "rag_status": "/collections/{id}/rag/status (GET)",
            "rag_stream": "/rag/stream/{task_id} (GET)",
            "rag_evaluate": "/collections/{id}/rag/evaluate (POST)",
            "rag_evaluation_summary": "/collections/{id}/rag/evaluation/summary (GET)"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/rag/stream/{task_id}")
async def stream_rag_response(task_id: str):
    """
    SSE endpoint for streaming RAG response.
    
    Args:
        task_id: Task identifier from query endpoint
        
    Returns:
        Server-Sent Events stream
    """
    # Import here to avoid circular imports
    from app.api.routes.collections_rag import _active_tasks
    
    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    async def event_generator():
        """Generate SSE events with real-time streaming."""
        task = _active_tasks[task_id]
        queue = task.get("queue")
        
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