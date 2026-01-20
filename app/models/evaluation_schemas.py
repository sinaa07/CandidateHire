"""Schemas for RAG evaluation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class EvaluationMetrics(BaseModel):
    """RAG evaluation metrics."""
    context_recall: float = Field(..., ge=0.0, le=1.0)
    faithfulness: float = Field(..., ge=0.0, le=1.0)
    answer_relevance: float = Field(..., ge=0.0, le=1.0)


class EvaluationRecord(BaseModel):
    """Single evaluation record."""
    collection_id: str
    question_id: str
    question: str
    expected_resumes: Optional[List[str]] = None
    retrieved_resumes: List[str]
    retrieved_chunks: List[str]
    answer: str
    metrics: EvaluationMetrics
    auto_fail: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class CollectionEvaluationSummary(BaseModel):
    """Aggregated evaluation metrics per collection."""
    collection_id: str
    total_questions: int
    avg_metrics: EvaluationMetrics
    failure_rate: float = Field(..., ge=0.0, le=1.0)
    hallucination_rate: float = Field(..., ge=0.0, le=1.0)
    rag_score: float = Field(..., ge=0.0, le=1.0)


class EvaluationRequest(BaseModel):
    """Request for RAG evaluation."""
    company_id: str
    question: str
    answer: str
    contexts: List[str] = Field(..., min_items=1)
    retrieved_resumes: List[str] = Field(..., min_items=1)
    expected_resumes: Optional[List[str]] = None
    ground_truth: Optional[str] = None


class EvaluationResponse(BaseModel):
    """Response from RAG evaluation."""
    question_id: str
    metrics: EvaluationMetrics
    auto_fail: bool
    failure_reasons: List[str] = Field(default_factory=list)