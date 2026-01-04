from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import collections_create, collections_process, collections_rank, collections_report
from app.api.routes import collections_rank_file
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