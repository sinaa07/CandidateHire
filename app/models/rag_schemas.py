from pydantic import BaseModel, Field
from typing import Optional, List


class RAGFilters(BaseModel):
    """Filters for RAG queries."""
    use_ranking: bool = True
    min_rank_position: Optional[int] = Field(None, ge=1)
    max_rank_position: Optional[int] = Field(None, ge=1)
    min_ranking_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    required_skills: Optional[List[str]] = Field(default_factory=list)


class RAGQueryRequest(BaseModel):
    """Request schema for RAG queries."""
    company_id: str
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    filters: Optional[RAGFilters] = Field(default_factory=RAGFilters)
    include_context: bool = True


class RAGStatusResponse(BaseModel):
    """Response schema for RAG status."""
    rag_available: bool
    features_enabled: dict
    index_built: bool
    index_stats: Optional[dict] = None


class RAGQueryResponse(BaseModel):
    """Response schema for RAG query (returns task_id)."""
    task_id: str
    status: str = "queued"


class RAGInitializeRequest(BaseModel):
    """Request schema for RAG initialization."""
    company_id: str


class RAGInitializeResponse(BaseModel):
    """Response schema for RAG initialization."""
    status: str
    collection_id: str
    details: dict
