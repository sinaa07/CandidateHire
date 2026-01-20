# RAG Evaluation Implementation

Minimal Ragas-based evaluation system for RAG accuracy tracking.

## Overview

This implementation provides:
- **Ragas evaluation** (faithfulness, context_recall, answer_relevance)
- **Auto-fail detection** for hallucinated answers
- **Per-collection metrics** aggregation
- **Simple storage** (JSON files per collection)

## Installation

```bash
pip install ragas datasets langchain
```

## API Endpoints

### 1. Evaluate RAG Query

```bash
POST /collections/{collection_id}/rag/evaluate
```

**Request:**
```json
{
  "company_id": "ac",
  "question": "Does the candidate have Kubernetes experience?",
  "answer": "Yes, candidate r_12 has Kubernetes experience.",
  "contexts": [
    "Implemented Kubernetes-based deployments and CI/CD pipelines.",
    "Worked as Backend Engineer at Flipkart for 3 years using Java."
  ],
  "retrieved_resumes": ["resume_12.txt", "resume_03.txt"],
  "expected_resumes": ["resume_12.txt"],  // optional
  "ground_truth": "Candidate r_12 has Kubernetes experience."  // optional
}
```

**Response:**
```json
{
  "question_id": "q_017",
  "metrics": {
    "context_recall": 1.0,
    "faithfulness": 0.96,
    "answer_relevance": 0.91
  },
  "auto_fail": false,
  "failure_reasons": []
}
```

### 2. Get Evaluation Summary

```bash
GET /collections/{collection_id}/rag/evaluation/summary?company_id={company_id}
```

**Response:**
```json
{
  "collection_id": "col_123",
  "total_questions": 40,
  "avg_metrics": {
    "context_recall": 0.88,
    "faithfulness": 0.93,
    "answer_relevance": 0.89
  },
  "failure_rate": 0.12,
  "hallucination_rate": 0.06,
  "rag_score": 0.90
}
```

### 3. Get Evaluation Records

```bash
GET /collections/{collection_id}/rag/evaluation/records?company_id={company_id}&limit=50
```

## Auto-Fail Rules

An answer is auto-failed if:

1. **Faithfulness < 0.85** - Low faithfulness score
2. **Context recall = 0** - No relevant context retrieved
3. **Answer mentions facts not in contexts** - Hallucination detected
4. **Answer references non-retrieved resumes** - When expected_resumes provided

## RAG Score Calculation

```
rag_score = 0.4 × context_recall + 0.4 × faithfulness + 0.2 × answer_relevance
```

**Score Interpretation:**
- ✅ **Green (≥ 0.85)**: High quality
- ⚠️ **Yellow (0.7-0.85)**: Acceptable
- ❌ **Red (< 0.7)**: Needs improvement

## Storage Structure

```
storage/companies/{company_id}/{collection_id}/rag/evaluations/
├── {question_id_1}.json
├── {question_id_2}.json
└── ...
```

Each evaluation record contains:
- Question, answer, contexts
- Retrieved resumes
- Ragas metrics
- Auto-fail status
- Timestamp

## Usage Example

```python
import requests

# After running a RAG query, evaluate it
response = requests.post(
    f"http://localhost:8000/collections/{collection_id}/rag/evaluate",
    json={
        "company_id": "ac",
        "question": "Who has Python experience?",
        "answer": "Candidates r_05 and r_12 have Python experience.",
        "contexts": [
            "Worked with Python for 5 years...",
            "Developed Python-based APIs..."
        ],
        "retrieved_resumes": ["resume_05.txt", "resume_12.txt"]
    }
)

result = response.json()
print(f"Faithfulness: {result['metrics']['faithfulness']}")
print(f"Auto-fail: {result['auto_fail']}")
```

## Integration Notes

- **Contexts**: Use candidate excerpts (300 chars) from `retrieve_candidates()`
- **Retrieved resumes**: Extract from candidate `filename` fields
- **Answer**: Full LLM response from RAG query
- **Evaluation is optional**: Run manually after RAG queries for accuracy tracking



priority:
Step-by-Step RAG Evaluation Workflow
Prerequisites Check
# 1. Ensure collection exists and Phase 2 is completeGET /collections/{collection_id}/rag/status?company_id={company_id}# 2. Verify RAG index is built (or build it)POST /collections/{collection_id}/rag/initializeBody: {"company_id": "your_company_id"}
Step 1: Prepare Test Questions
Create a small set of evaluation questions (5–10):
Example Questions:
"Who has Kubernetes experience?"
"Find candidates with Python and AWS skills"
"Which candidates worked at companies similar to [JD company]?"
"Who has 5+ years of backend experience?"
"Show me candidates with machine learning experience"
Store these in a file (e.g., test_questions.json):
[  {"question": "Who has Kubernetes experience?", "expected_resumes": ["resume_12.txt"]},  {"question": "Find Python developers", "expected_resumes": ["resume_05.txt", "resume_08.txt"]}]
Step 2: Run RAG Queries
For each question, run a RAG query:
# Submit queryPOST /collections/{collection_id}/rag/queryBody: {  "company_id": "your_company_id",  "query": "Who has Kubernetes experience?",  "top_k": 5,  "include_context": true}# Response gives task_id, then stream answer:GET /rag/stream/{task_id}
Capture:
The question
The full answer (from stream)
The retrieved resume filenames (from candidates)
The context excerpts (from candidates)
Step 3: Evaluate Each Query
For each RAG query result, call the evaluation endpoint:
POST /collections/{collection_id}/rag/evaluateBody: {  "company_id": "your_company_id",  "question": "Who has Kubernetes experience?",  "answer": "<full LLM response from Step 2>",  "contexts": [    "<excerpt from candidate 1>",    "<excerpt from candidate 2>",    ...  ],  "retrieved_resumes": ["resume_12.txt", "resume_03.txt"],  "expected_resumes": ["resume_12.txt"]  // if you know ground truth}
Check the response:
auto_fail: true/false
metrics.faithfulness (should be ≥ 0.85)
metrics.context_recall (should be > 0)
failure_reasons (if any)
Step 4: Review Collection Summary
After evaluating 5–10 questions:
GET /collections/{collection_id}/rag/evaluation/summary?company_id={company_id}
Check:
rag_score (target: ≥ 0.85)
failure_rate (target: < 0.15)
hallucination_rate (target: < 0.10)
avg_metrics.faithfulness (target: ≥ 0.90)
Step 5: Review Individual Records
GET /collections/{collection_id}/rag/evaluation/records?company_id={company_id}&limit=20
Look for:
Questions with auto_fail: true
Low faithfulness scores (< 0.85)
Zero context_recall (retrieval issues)
Step 6: Iterate and Improve
Based on results:
If faithfulness is low → check prompt engineering or LLM provider
If context_recall is low → improve retrieval (top_k, embeddings, filters)
If answer_relevance is low → refine questions or system prompts
Quick Test Script Flow
# 1. Check statuscurl "http://localhost:8000/collections/{id}/rag/status?company_id={company_id}"# 2. Run querycurl -X POST "http://localhost:8000/collections/{id}/rag/query" \  -H "Content-Type: application/json" \  -d '{"company_id": "...", "query": "Who has Python?", "top_k": 5}'# 3. Evaluate (after getting answer)curl -X POST "http://localhost:8000/collections/{id}/rag/evaluate" \  -H "Content-Type: application/json" \  -d '{"company_id": "...", "question": "...", "answer": "...", "contexts": [...], "retrieved_resumes": [...]}'# 4. Check summarycurl "http://localhost:8000/collections/{id}/rag/evaluation/summary?company_id={company_id}"
Recommended Starting Point
Start with 3–5 simple questions (single skill/technology)
Evaluate each immediately after query
Check for auto-fails
Review summary after 5 evaluations
Expand to 10–20 questions for a more reliable baseline
Focus areas:
Faithfulness (hallucination detection)
Context recall (retrieval quality)
Auto-fail rate (safety threshold)
This gives you a baseline and highlights issues to address.