from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.routes import collections_create, collections_process, collections_rank, collections_report
from app.api.routes import collections_rank_file, collections_rag, collections_evaluate
from app.api.routes.v2 import companies, jobs, dashboard, resumes, pipeline
import asyncio
import logging
import os
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
    else:
        load_dotenv()
except ImportError:
    pass


def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    extra = os.getenv("CORS_ORIGINS") or os.getenv("NEXT_PUBLIC_API_URL") or ""
    for origin in extra.split(","):
        origin = origin.strip()
        if origin and origin not in origins:
            origins.append(origin)
    return origins


app = FastAPI(
    title="CandidateHire API",
    description="Resume ranking and processing system",
    version="1.0.0",
)


@app.on_event("startup")
def _startup_init() -> None:
    from app.models.db import init_db
    from app.utils.model_cache import ModelCache

    init_db()
    ModelCache.get_instance()


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": "not found", "detail": str(exc.detail)},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "detail": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s\n%s", request.method, request.url.path, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "internal error"},
    )


# Include routers
app.include_router(collections_rank_file.router)
app.include_router(collections_create.router)
app.include_router(collections_process.router)
app.include_router(collections_rank.router)
app.include_router(collections_report.router)
app.include_router(collections_rag.router)
app.include_router(collections_evaluate.router)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)
app.include_router(resumes.router)
app.include_router(pipeline.router)


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
            "rag_evaluation_summary": "/collections/{id}/rag/evaluation/summary (GET)",
            "v2_dashboard": "/api/v2/companies/{company_id}/dashboard (GET)",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/health/models")
async def health_models():
    from app.utils.model_cache import ModelCache

    return ModelCache.get_models_health()


@app.get("/rag/stream/{task_id}")
async def stream_rag_response(task_id: str):
    from app.api.routes.collections_rag import _active_tasks

    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        task = _active_tasks[task_id]
        queue = task.get("queue")

        if not queue:
            yield f"data: Error: Task queue not found\n\n"
            return

        wait_count = 0
        while task["status"] == "queued" and wait_count < 20:
            await asyncio.sleep(0.5)
            wait_count += 1

        if task["status"] == "queued":
            yield f"data: Error: Task timeout\n\n"
            return

        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=60.0)
                if chunk is None:
                    break
                yield f"data: {chunk}\n\n"
            except asyncio.TimeoutError:
                yield f"data: Error: Stream timeout\n\n"
                break
            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"
                break

        if task.get("status") == "failed":
            error = task.get("error", "Unknown error")
            yield f"data: Error: {error}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
