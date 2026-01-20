"""RAG evaluation API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.evaluation_schemas import (
    EvaluationRequest, EvaluationResponse, CollectionEvaluationSummary
)
from app.models.rag_schemas import RAGQueryRequest
from app.services.evaluation_service import (
    evaluate_rag_query, compute_collection_summary, load_evaluation_records
)
from app.utils.paths import get_collection_root, assert_collection_exists
from app.core.errors import to_http_error
from app.services.rag_service import process_rag_query
import asyncio

router = APIRouter(prefix="/collections", tags=["evaluation"])


@router.post("/{collection_id}/rag/evaluate", response_model=EvaluationResponse)
async def evaluate_rag_endpoint(
    collection_id: str,
    request: EvaluationRequest
) -> EvaluationResponse:
    """
    Evaluate a RAG query using Ragas.
    
    Args:
        collection_id: Collection identifier
        request: Evaluation request with question, answer, contexts
        
    Returns:
        Evaluation results with metrics and auto-fail status
    """
    try:
        collection_root = get_collection_root(request.company_id, collection_id)
        assert_collection_exists(collection_root)
        
        # Run evaluation
        record = evaluate_rag_query(
            company_id=request.company_id,
            collection_id=collection_id,
            question=request.question,
            answer=request.answer,
            contexts=request.contexts,
            retrieved_resumes=request.retrieved_resumes,
            expected_resumes=request.expected_resumes,
            ground_truth=request.ground_truth
        )
        
        # Extract failure reasons
        failure_reasons = []
        if record.auto_fail:
            if record.metrics.faithfulness < 0.75:
                failure_reasons.append("Low faithfulness score")
            if record.metrics.context_recall == 0.0:
                failure_reasons.append("No relevant context")
        
        return EvaluationResponse(
            question_id=record.question_id,
            metrics=record.metrics,
            auto_fail=record.auto_fail,
            failure_reasons=failure_reasons
        )
        
    except Exception as exc:
        raise to_http_error(exc)


@router.get("/{collection_id}/rag/evaluation/summary", response_model=CollectionEvaluationSummary)
async def get_evaluation_summary(
    collection_id: str,
    company_id: str = Query(..., description="Company identifier")
) -> CollectionEvaluationSummary:
    """
    Get aggregated evaluation summary for a collection.
    
    Args:
        collection_id: Collection identifier
        company_id: Company identifier (query parameter)
        
    Returns:
        Collection evaluation summary
    """
    try:
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        summary = compute_collection_summary(company_id, collection_id)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail="No evaluation records found for this collection"
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_error(exc)


@router.get("/{collection_id}/rag/evaluation/records")
async def get_evaluation_records(
    collection_id: str,
    company_id: str = Query(..., description="Company identifier"),
    limit: int = Query(50, ge=1, le=100)
) -> dict:
    """
    Get evaluation records for a collection.
    
    Args:
        collection_id: Collection identifier
        company_id: Company identifier (query parameter)
        limit: Maximum number of records to return
        
    Returns:
        List of evaluation records
    """
    try:
        collection_root = get_collection_root(company_id, collection_id)
        assert_collection_exists(collection_root)
        
        records = load_evaluation_records(company_id, collection_id)
        
        return {
            "total": len(records),
            "records": [r.model_dump() for r in records[:limit]]
        }
        
    except Exception as exc:
        raise to_http_error(exc)