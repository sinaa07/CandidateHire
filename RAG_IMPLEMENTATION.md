# RAG System Implementation

## Overview

The RAG (Retrieval-Augmented Generation) system enables natural language queries over candidate resumes using semantic search and LLM responses. It integrates seamlessly with existing Phase 2 (processing) and Phase 3 (ranking) workflows.

## Architecture

### Components

1. **Embeddings** (`app/utils/embeddings.py`): Uses sentence-transformers (all-MiniLM-L6-v2) for 384-dim embeddings
2. **FAISS Index** (`app/utils/faiss_index.py`): Vector storage using IndexFlatL2 (GPU placeholder comments included)
3. **Retrieval** (`app/utils/rag_retrieval.py`): Two-stage retrieval with FAISS + re-ranking
4. **LLM Service** (`app/services/llm_service.py`): OpenAI/Anthropic integration with streaming support
5. **RAG Service** (`app/services/rag_service.py`): Core orchestration with lazy index building
6. **API Routes** (`app/api/routes/collections_rag.py`): REST endpoints with SSE streaming

### Storage Structure

```
storage/companies/{company_id}/{collection_id}/rag/
├── index/
│   ├── faiss_index.index
│   ├── embeddings.npy
│   ├── resume_mapping.json
│   └── index_meta.json
├── cache/
│   └── {query_hash}.json
└── conversations/ (optional, future)
```

## API Endpoints

### POST `/collections/{collection_id}/rag/initialize`
Manually trigger index build (optional, lazy building on first query).

**Request:**
```json
{
  "company_id": "string"
}
```

### GET `/collections/{collection_id}/rag/status?company_id={company_id}`
Check RAG availability and index status.

**Response:**
```json
{
  "rag_available": true,
  "features_enabled": {
    "phase2_complete": true,
    "phase3_available": true,
    "llm_providers": ["openai"]
  },
  "index_built": true,
  "index_stats": {...}
}
```

### POST `/collections/{collection_id}/rag/query`
Submit RAG query (async, returns task_id).

**Request:**
```json
{
  "company_id": "string",
  "query": "Find candidates with Python experience",
  "top_k": 5,
  "filters": {
    "use_ranking": true,
    "min_rank_position": 1,
    "max_rank_position": 20,
    "min_ranking_score": 0.7,
    "required_skills": ["Python"]
  },
  "include_context": true
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "status": "queued"
}
```

### GET `/rag/stream/{task_id}`
SSE endpoint for streaming LLM response.

**Response:** Server-Sent Events stream with `text/event-stream` content type.

## Retrieval Algorithm

### Stage 1: FAISS Semantic Search
1. Convert query to 384-dim embedding
2. Search FAISS index (IndexFlatL2 with L2 normalization for cosine similarity)
3. Return top 50 candidates by similarity

### Stage 2: Re-ranking (if Phase 3 available)
1. Load `ranking_results.json` from Phase 3
2. For each candidate:
   - Combined score = 0.4 × FAISS_similarity + 0.3 × Phase3_score + 0.3 × skill_score
3. Apply filters (rank range, required skills, min score)
4. Sort by combined score, return top_k

**Fallback (no Phase 3):** Combined score = 0.6 × FAISS + 0.4 × skills

## Features

- **Lazy Index Building**: Automatically builds index on first query if Phase 2 complete
- **Query Caching**: SHA-256 hash-based caching with 1-hour TTL
- **Company Isolation**: Path validation prevents cross-company access
- **Streaming Responses**: Real-time SSE streaming of LLM responses
- **Multi-Provider LLM**: Supports OpenAI and Anthropic with automatic provider selection
- **Free Tier Detection**: Graceful handling of rate limits and quotas
- **Skill Extraction**: Reuses Phase 3 skill extraction utilities

## Dependencies

- `sentence-transformers>=2.2.0`: Embeddings
- `faiss-cpu>=1.7.4`: Vector search (GPU version available)
- `openai>=1.0.0`: OpenAI API client
- `anthropic>=0.18.0`: Anthropic API client

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)

## Integration

The RAG system integrates with existing phases:
- **Phase 2 (Required)**: Processes resumes to `.txt` format
- **Phase 3 (Optional)**: Enhances retrieval with ranking scores

Index building is lazy-initialized on first query, ensuring no overhead until needed.

## Error Handling

All endpoints use centralized error handling via `to_http_error()`:
- 404: Collection/index not found
- 400: Validation errors
- 500: Internal server errors (no stack trace leakage)

## Performance Considerations

- FAISS index uses IndexFlatL2 (exact search, suitable for <100K vectors)
- GPU support: Comments indicate where to add GPU resources
- Query caching reduces LLM API calls
- Async processing prevents blocking API responses
