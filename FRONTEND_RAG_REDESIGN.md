# Frontend & RAG System: Structure & Redesign Guide

## Frontend Architecture

**Tech Stack:** Next.js 14 (App Router), TypeScript, React Context API, Tailwind CSS + shadcn/ui, SSE streaming

**Component Structure:**
```
frontend/src/
├── components/
│   ├── phases/          # Phase1Upload, Phase2Process, Phase3Rank, Phase4Results
│   ├── features/        # ResultsTable, FiltersBar, CompareSelectionBar
│   ├── modals/          # ReRankModal, ComparisonModal
│   └── layout/          # PhaseStepper (4-phase progress), TopNav
├── contexts/AppContext.tsx    # Global state (phase, collection_id, results, filters)
└── utils/
    ├── api.ts           # API client (createCollection, processCollection, rankCollection, getReport)
    ├── formatters.ts    # Score/date formatting
    └── storage.ts       # LocalStorage helpers
```

**State Flow:** Upload (Phase 1) → Process (Phase 2) → Rank (Phase 3) → Results (Phase 4). State persists in Context + localStorage.

---

## RAG System Structure

**Architecture:** RAG enables natural language queries over resumes using semantic search + LLM responses.

**Components:**
1. **Embeddings** (`app/utils/embeddings.py`): sentence-transformers (all-MiniLM-L6-v2, 384-dim)
2. **FAISS Index** (`app/utils/faiss_index.py`): Vector storage (IndexFlatL2)
3. **Retrieval** (`app/utils/rag_retrieval.py`): Two-stage (FAISS → re-ranking with Phase 3 scores)
4. **LLM Service** (`app/services/llm_service.py`): OpenAI/Anthropic streaming
5. **RAG Service** (`app/services/rag_service.py`): Orchestration, lazy index building
6. **API Routes** (`app/api/routes/collections_rag.py`): REST + SSE streaming

**Storage:** `storage/companies/{company_id}/{collection_id}/rag/`
- `index/`: faiss_index.index, embeddings.npy, resume_mapping.json, index_meta.json
- `cache/`: Query cache (SHA-256 hash, 1-hour TTL)

**Retrieval Algorithm:**
- Stage 1: FAISS semantic search (top 50 by cosine similarity)
- Stage 2: Re-ranking (if Phase 3 available): 0.4 × FAISS + 0.3 × Phase3_score + 0.3 × skill_score
- Filters: rank range, required skills, min score

**Features:** Lazy index building, query caching, SSE streaming, multi-provider LLM (OpenAI/Anthropic)

---

## UI/UX Redesign Recommendations

### Phase 1: Upload
- File preview (list ZIP contents before upload), progress bar, validation feedback, recent collections dropdown

### Phase 2: Process
- Real-time progress updates (polling/WebSocket), processing breakdown (extraction/validation/duplicates), file-level error details, auto-advance when complete

### Phase 3: Rank
- JD file upload option (API supports `/rank-file`), JD preview/edit, Top-K selector, estimated time, JD template saving

### Phase 4: Results
- **RAG Chat Interface** (sidebar): Natural language queries ("Find candidates with 5+ years Python", "Show top 3 React/TypeScript candidates")
- Real-time streaming response display, query history, export (CSV/PDF), candidate detail modal, enhanced comparison view

### New Phase 5: RAG Chat (Recommended)
- Dedicated chat interface, query suggestions, context-aware responses, export conversation/insights

---

## API Endpoints

### Phase 1: Create Collection
**POST** `/collections/create`
- Body: `FormData` (company_id, zip_file)
- Response: `{ status, collection_id, company_id }`

### Phase 2: Process Collection
**POST** `/collections/{collection_id}/process`
- Body: `{ company_id }`
- Response: `{ status, collection_id, details: { stats, reports_generated } }`

### Phase 3: Rank Collection
**POST** `/collections/{collection_id}/rank`
- Body: `{ company_id, jd_text, top_k? }`
- Response: `{ status, collection_id, details: { ranked_count, outputs_generated } }`

**POST** `/collections/{collection_id}/rank-file`
- Body: `FormData` (company_id, jd_file, top_k?)

### Phase 4: Reports
**GET** `/collections/{collection_id}/report?company_id={id}&include_results=true`
- Response: `{ collection_id, meta, phase2: { validation_report, duplicate_report }, phase3: { ranking_summary, ranking_results? } }`

**GET** `/collections/{collection_id}/outputs?company_id={id}`
- Response: `{ outputs: { ranking_results.json: bool, ranking_results.csv: bool } }`

### RAG Endpoints
**GET** `/collections/{collection_id}/rag/status?company_id={id}`
- Response: `{ rag_available, features_enabled, index_built, index_stats }`

**POST** `/collections/{collection_id}/rag/initialize`
- Body: `{ company_id }`
- Response: `{ status, collection_id, details: { num_vectors, dimension } }`

**POST** `/collections/{collection_id}/rag/query`
- Body: `{ company_id, query, top_k?, filters?, include_context? }`
- Response: `{ task_id, status: "queued" }`

**GET** `/rag/stream/{task_id}` (SSE)
- Response: Server-Sent Events stream (`text/event-stream`), format: `data: {chunk}\n\n`

---

## Implementation Phases

**Phase A: Enhance Existing UI**
1. Progress indicators (Phase 2/3), improved error handling, candidate detail modals, enhanced comparison view

**Phase B: Integrate RAG**
1. RAG status check in Phase 4, chat interface component, SSE streaming integration, query history/suggestions

**Phase C: Advanced Features**
1. JD template management, export (PDF reports), collection history, analytics dashboard

---

## Frontend API Integration Pattern

```typescript
// RAG Query Integration Example
async function queryRAG(collectionId: string, companyId: string, query: string) {
  // 1. Submit query
  const response = await fetch(`/collections/${collectionId}/rag/query`, {
    method: 'POST',
    body: JSON.stringify({ company_id: companyId, query, top_k: 5 })
  });
  const { task_id } = await response.json();
  
  // 2. Stream response via SSE
  const eventSource = new EventSource(`/rag/stream/${task_id}`);
  eventSource.onmessage = (e) => {
    const chunk = e.data;
    // Update UI with streaming text
  };
}
```

---

## Key Design Principles

1. **Progressive Disclosure**: Details on demand (modals, expandable rows)
2. **Real-time Feedback**: Progress bars, streaming responses, status updates
3. **Error Recovery**: Clear messages with actionable steps
4. **Contextual Help**: Tooltips, query suggestions, inline docs
5. **Responsive Design**: Mobile-friendly layouts
