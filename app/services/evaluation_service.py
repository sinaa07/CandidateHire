"""RAG evaluation service using Ragas."""
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, UTC
from datasets import Dataset
from ragas import evaluate
from ragas.metrics.collections import faithfulness, context_recall, answer_relevancy
from app.models.evaluation_schemas import (
    EvaluationRecord, CollectionEvaluationSummary, EvaluationMetrics
)
from app.utils.paths import get_collection_root

logger = logging.getLogger(__name__)

# Auto-fail thresholds
FAITHFULNESS_THRESHOLD = 0.85
MIN_CONTEXT_RECALL = 0.0  # Will fail if no supporting context


def get_evaluation_path(company_id: str, collection_id: str) -> Path:
    """Get evaluation storage path."""
    collection_root = get_collection_root(company_id, collection_id)
    return collection_root / "rag" / "evaluations"


def evaluate_rag(
    question: str,
    answer: str,
    contexts: List[str],
    ground_truth: Optional[str] = None
) -> Dict[str, float]:
    """
    Evaluate RAG response using Ragas.
    
    Args:
        question: User question
        answer: LLM answer
        contexts: Retrieved context chunks
        ground_truth: Optional ground truth answer
        
    Returns:
        Dictionary with metric scores
    """
    try:
        # Prepare dataset for Ragas
        data_dict = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts]
        }
        
        if ground_truth:
            data_dict["ground_truth"] = [ground_truth]
        
        dataset = Dataset.from_dict(data_dict)
        
        # Run evaluation
        metrics = [faithfulness, context_recall, answer_relevancy]
        results = evaluate(dataset, metrics=metrics)
        
        # Extract scores (ragas returns 'answer_relevancy' but we use 'answer_relevance' in our schema)
        scores = {
            "faithfulness": float(results["faithfulness"][0]) if "faithfulness" in results else 0.0,
            "context_recall": float(results["context_recall"][0]) if "context_recall" in results else 0.0,
            "answer_relevance": float(results["answer_relevancy"][0]) if "answer_relevancy" in results else 0.0
        }
        
        logger.info(f"Ragas evaluation completed: {scores}")
        return scores
        
    except Exception as e:
        logger.error(f"Ragas evaluation error: {e}", exc_info=True)
        # Return default scores on error
        return {
            "faithfulness": 0.0,
            "context_recall": 0.0,
            "answer_relevance": 0.0
        }


def check_auto_fail(
    answer: str,
    contexts: List[str],
    metrics: EvaluationMetrics,
    retrieved_resumes: List[str],
    expected_resumes: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """
    Check if answer should be auto-failed.
    
    Args:
        answer: LLM answer
        contexts: Retrieved context chunks
        metrics: Evaluation metrics
        retrieved_resumes: List of retrieved resume filenames
        expected_resumes: Optional expected resume filenames
        
    Returns:
        Tuple of (auto_fail, failure_reasons)
    """
    failure_reasons = []
    
    # Rule 1: Faithfulness threshold
    if metrics.faithfulness < FAITHFULNESS_THRESHOLD:
        failure_reasons.append(f"Faithfulness score {metrics.faithfulness:.2f} below threshold {FAITHFULNESS_THRESHOLD}")
    
    # Rule 2: No supporting context
    if metrics.context_recall == 0.0:
        failure_reasons.append("No relevant context retrieved (context_recall = 0)")
    
    # Rule 3: Answer mentions facts not in contexts
    context_text = " ".join(contexts).lower()
    answer_lower = answer.lower()
    
    # Check for common skill/tech mentions not in context
    suspicious_terms = []
    for term in ["aws", "kubernetes", "docker", "python", "java", "react", "node.js"]:
        if term in answer_lower and term not in context_text:
            suspicious_terms.append(term)
    
    if suspicious_terms:
        failure_reasons.append(f"Answer mentions terms not in context: {', '.join(suspicious_terms)}")
    
    # Rule 4: Answer mentions resume not in retrieved set
    # Extract resume mentions from answer (simple heuristic)
    for resume in retrieved_resumes:
        if resume.replace(".txt", "").replace(".pdf", "") in answer:
            continue
    # If expected resumes provided, check if answer mentions non-retrieved ones
    if expected_resumes:
        mentioned_resumes = [r for r in expected_resumes if r.replace(".txt", "").replace(".pdf", "") in answer_lower]
        missing_resumes = [r for r in mentioned_resumes if r not in retrieved_resumes]
        if missing_resumes:
            failure_reasons.append(f"Answer references resumes not retrieved: {', '.join(missing_resumes[:3])}")
    
    auto_fail = len(failure_reasons) > 0
    return auto_fail, failure_reasons


def save_evaluation_record(
    company_id: str,
    collection_id: str,
    record: EvaluationRecord
) -> None:
    """Save evaluation record to disk."""
    eval_path = get_evaluation_path(company_id, collection_id)
    eval_path.mkdir(parents=True, exist_ok=True)
    
    record_file = eval_path / f"{record.question_id}.json"
    with open(record_file, 'w') as f:
        json.dump(record.model_dump(), f, indent=2)
    
    logger.info(f"Saved evaluation record: {record_file}")


def load_evaluation_records(
    company_id: str,
    collection_id: str
) -> List[EvaluationRecord]:
    """Load all evaluation records for a collection."""
    eval_path = get_evaluation_path(company_id, collection_id)
    
    if not eval_path.exists():
        return []
    
    records = []
    for record_file in eval_path.glob("*.json"):
        try:
            with open(record_file, 'r') as f:
                data = json.load(f)
                records.append(EvaluationRecord(**data))
        except Exception as e:
            logger.warning(f"Failed to load evaluation record {record_file}: {e}")
    
    return sorted(records, key=lambda x: x.timestamp, reverse=True)


def compute_collection_summary(
    company_id: str,
    collection_id: str
) -> Optional[CollectionEvaluationSummary]:
    """Compute aggregated evaluation summary for a collection."""
    records = load_evaluation_records(company_id, collection_id)
    
    if not records:
        return None
    
    total = len(records)
    
    # Aggregate metrics
    total_faithfulness = sum(r.metrics.faithfulness for r in records)
    total_context_recall = sum(r.metrics.context_recall for r in records)
    total_answer_relevance = sum(r.metrics.answer_relevance for r in records)
    
    avg_metrics = EvaluationMetrics(
        faithfulness=total_faithfulness / total,
        context_recall=total_context_recall / total,
        answer_relevance=total_answer_relevance / total
    )
    
    # Compute failure rates
    failed_count = sum(1 for r in records if r.auto_fail)
    hallucination_count = sum(1 for r in records if r.metrics.faithfulness < FAITHFULNESS_THRESHOLD)
    
    failure_rate = failed_count / total
    hallucination_rate = hallucination_count / total
    
    # Compute RAG score
    rag_score = (
        0.4 * avg_metrics.context_recall +
        0.4 * avg_metrics.faithfulness +
        0.2 * avg_metrics.answer_relevance
    )
    
    return CollectionEvaluationSummary(
        collection_id=collection_id,
        total_questions=total,
        avg_metrics=avg_metrics,
        failure_rate=failure_rate,
        hallucination_rate=hallucination_rate,
        rag_score=rag_score
    )


def evaluate_rag_query(
    company_id: str,
    collection_id: str,
    question: str,
    answer: str,
    contexts: List[str],
    retrieved_resumes: List[str],
    expected_resumes: Optional[List[str]] = None,
    ground_truth: Optional[str] = None
) -> EvaluationRecord:
    """
    Evaluate a RAG query and save the record.
    
    Args:
        company_id: Company identifier
        collection_id: Collection identifier
        question: User question
        answer: LLM answer
        contexts: Retrieved context chunks
        retrieved_resumes: List of retrieved resume filenames
        expected_resumes: Optional expected resume filenames
        ground_truth: Optional ground truth answer
        
    Returns:
        Evaluation record
    """
    # Run Ragas evaluation
    scores = evaluate_rag(question, answer, contexts, ground_truth)
    
    metrics = EvaluationMetrics(
        faithfulness=scores["faithfulness"],
        context_recall=scores["context_recall"],
        answer_relevance=scores["answer_relevance"]
    )
    
    # Check auto-fail
    auto_fail, failure_reasons = check_auto_fail(
        answer, contexts, metrics, retrieved_resumes, expected_resumes
    )
    
    # Create record
    question_id = str(uuid.uuid4())
    record = EvaluationRecord(
        collection_id=collection_id,
        question_id=question_id,
        question=question,
        expected_resumes=expected_resumes,
        retrieved_resumes=retrieved_resumes,
        retrieved_chunks=contexts,
        answer=answer,
        metrics=metrics,
        auto_fail=auto_fail,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    
    # Save record
    save_evaluation_record(company_id, collection_id, record)
    
    logger.info(f"Evaluation completed for {question_id}: auto_fail={auto_fail}, metrics={metrics}")
    
    return record