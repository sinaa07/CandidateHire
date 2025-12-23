from fastapi import FastAPI
from app.api.routes import collections_create, collections_process, collections_rank, collections_report

app = FastAPI(
    title="CandidateHire API",
    description="Resume ranking and processing system",
    version="1.0.0"
)

# Include routers
app.include_router(collections_create.router)      # Phase 1 - create collection
app.include_router(collections_process.router)     # Phase 2 - process
app.include_router(collections_rank.router)        # Phase 3 - rank
app.include_router(collections_report.router)      # Phase 4 - reports

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
            "outputs": "/collections/{id}/outputs (GET)"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}