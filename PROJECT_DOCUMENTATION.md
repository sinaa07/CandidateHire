# ResumeRanker - Project Documentation

## Overview

ResumeRanker is an AI-powered resume processing and ranking system that processes resume collections and ranks them against job descriptions. The system features a 4-phase workflow with an integrated RAG (Retrieval-Augmented Generation) chat interface for natural language candidate queries.

**Tech Stack:**
- **Backend:** FastAPI (Python)
- **Frontend:** Next.js 14 (TypeScript, React)
- **ML/NLP:** sentence-transformers, FAISS, TF-IDF, scikit-learn
- **Text Extraction:** PyPDF2, python-docx, pytesseract (OCR)
- **LLM:** OpenAI, Anthropic (Claude)
- **Styling:** Tailwind CSS, Inter font

---

## Architecture

### Project Structure

```
hire/
├── app/                          # Backend application
│   ├── main.py                  # FastAPI app & CORS setup
│   ├── api/routes/              # API route handlers
│   │   ├── collections_create.py    # Phase 1
│   │   ├── collections_process.py  # Phase 2
│   │   ├── collections_rank.py     # Phase 3
│   │   ├── collections_rank_file.py # Phase 3 (file upload)
│   │   ├── collections_report.py   # Phase 4
│   │   └── collections_rag.py      # RAG endpoints
│   ├── services/                # Business logic
│   │   ├── collection_service.py
│   │   ├── processing_service.py
│   │   ├── ranking_service.py
│   │   ├── rag_service.py        # RAG orchestration
│   │   └── llm_service.py        # LLM integration
│   ├── utils/                   # Utilities
│   │   ├── embeddings.py        # Sentence transformers
│   │   ├── faiss_index.py        # Vector index
│   │   ├── rag_retrieval.py      # RAG retrieval
│   │   ├── text_extraction.py     # PDF/DOCX/TXT + OCR
│   │   ├── vectorization.py      # TF-IDF
│   │   └── skills.py            # Skill extraction
│   └── models/                  # Pydantic schemas
├── frontend/                     # Next.js frontend
│   ├── src/components/
│   │   ├── phases/              # Phase UI components
│   │   ├── features/
│   │   │   ├── RAGChat.tsx     # RAG chat interface
│   │   │   └── ResultsTable.tsx
│   │   └── layout/
│   ├── contexts/AppContext.tsx  # Global state
│   └── utils/api.ts            # API client
└── storage/                     # Data directory
    └── companies/{company_id}/{collection_id}/
        ├── input/raw/           # Extracted ZIP
        ├── processed/           # Extracted text (.txt)
        ├── outputs/             # Ranking results
        ├── reports/             # Processing reports
        └── rag/                 # RAG index & cache
            ├── index/           # FAISS index
            └── cache/           # Query cache
```

---

## 4-Phase Workflow

### Phase 1: Collection Creation (Upload)

**Purpose:** Upload and extract resume ZIP files

**API:** `POST /collections/create`

**Process:**
1. Generate unique `collection_id` (UUID)
2. Extract ZIP to `input/raw/`
3. Create `collection_meta.json`

**Output:** Directory structure with extracted files

---

### Phase 2: Processing (Text Extraction & Validation)

**Purpose:** Extract text, validate, and detect duplicates

**API:** `POST /collections/{collection_id}/process`

**Process:**
1. Extract text from PDF/DOCX/TXT files
   - **PDFs:** Regular extraction with OCR fallback for image-based PDFs
   - **DOCX/TXT:** Direct extraction
2. Validate text (non-empty, meaningful content)
3. Compute SHA-256 hashes for duplicate detection
4. Save to `processed/{filename}.txt`
5. Generate validation and duplicate reports

**Features:**
- Automatic OCR for image-based PDFs
- Duplicate detection via content hashing
- Detailed validation reports

**Output:** Processed text files, validation report, duplicate report

---

### Phase 3: Ranking (Resume Scoring)

**Purpose:** Rank resumes against job description

**APIs:**
- `POST /collections/{collection_id}/rank` (JD as text)
- `POST /collections/{collection_id}/rank-file` (JD as file)

**Process:**
1. Extract JD text (from input or file)
2. Build TF-IDF vectorizer on resumes
3. For each resume:
   - Compute TF-IDF cosine similarity (70% weight)
   - Extract and match skills (30% weight)
   - Calculate final score
4. Sort by score (descending)
5. Apply `top_k` filter if specified
6. Generate JSON/CSV outputs

**Scoring:**
- **TF-IDF Score:** Semantic similarity (0-1)
- **Skill Score:** Skill overlap ratio (0-1)
- **Final Score:** 0.7 × TF-IDF + 0.3 × Skill

**Output:** Ranking results (JSON, CSV), ranking summary, ML artifacts

---

### Phase 4: Results & RAG Chat

**Purpose:** View results and query candidates with natural language

**APIs:**
- `GET /collections/{collection_id}/report` - Get reports
- `GET /collections/{collection_id}/rag/status` - RAG status
- `POST /collections/{collection_id}/rag/query` - Submit query
- `GET /rag/stream/{task_id}` - Stream response (SSE)

**Features:**
- **Results Dashboard:** Card-based layout with summary stats
- **Results Table:** Sortable, filterable candidate list
- **Comparison Mode:** Compare up to 3 candidates side-by-side
- **RAG Chat Interface:**
  - Natural language queries ("Find Python developers with 5+ years")
  - Real-time streaming responses via Server-Sent Events
  - Query suggestions and history
  - Context-aware responses using Phase 3 ranking

**RAG System:**
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384-dim)
- **Vector Search:** FAISS IndexFlatL2
- **Retrieval:** Two-stage (FAISS semantic search → re-ranking with Phase 3 scores)
- **LLM:** OpenAI/Anthropic with streaming support
- **Caching:** SHA-256 hash-based, 1-hour TTL

**Output:** Full reports, ranking results, interactive chat interface

---

## RAG System Architecture

### Components

1. **Embeddings** (`app/utils/embeddings.py`): Sentence transformers for 384-dim embeddings
2. **FAISS Index** (`app/utils/faiss_index.py`): Vector storage (IndexFlatL2)
3. **Retrieval** (`app/utils/rag_retrieval.py`): Two-stage retrieval with re-ranking
4. **LLM Service** (`app/services/llm_service.py`): Multi-provider LLM with streaming
5. **RAG Service** (`app/services/rag_service.py`): Orchestration, lazy index building
6. **API Routes** (`app/api/routes/collections_rag.py`): REST + SSE streaming

### Retrieval Algorithm

1. **Stage 1:** FAISS semantic search (top 50 by cosine similarity)
2. **Stage 2:** Re-ranking (if Phase 3 available):
   - Combined: 0.4 × FAISS + 0.3 × Phase3_score + 0.3 × skill_score
3. **Filters:** Rank range, required skills, min score
4. **LLM Response:** Streamed via SSE with context from retrieved candidates

### Features

- Lazy index building (auto-builds on first query)
- Query caching (SHA-256 hash, 1-hour TTL)
- Multi-provider LLM (OpenAI/Anthropic)
- Real-time streaming responses
- Context-aware using Phase 3 ranking

---

## Frontend Design

### Design System

**Color Palette:**
- Primary: #6366F1 (Royal Purple)
- Success: #10B981 (Emerald)
- Warning: #F59E0B (Amber)
- Error: #EF4444 (Rose)
- Neutrals: #FFFFFF → #F5F5F5 → #E5E5E5 → #262626

**Typography:**
- Font: Inter (400, 500, 600, 700)
- Mono: JetBrains Mono (code/data)

**Layout:**
- 3-panel layout: Main content + RAG Chat sidebar (420px)
- Responsive: Mobile drawer, tablet toggle, desktop full layout
- Phase stepper with progress indicators

### Key Components

- **Phase1Upload:** Drag-drop ZIP upload with file preview
- **Phase2Process:** Real-time progress with breakdown stats
- **Phase3Rank:** Split-view (JD input + config panel)
- **Phase4Results:** Dashboard with cards, table, filters
- **RAGChat:** Chat interface with streaming, suggestions, history

---

## API Routes Summary

| Method | Route | Phase | Description |
|--------|-------|-------|-------------|
| `POST` | `/collections/create` | 1 | Upload ZIP, create collection |
| `POST` | `/collections/{id}/process` | 2 | Process resumes |
| `POST` | `/collections/{id}/rank` | 3 | Rank (JD as text) |
| `POST` | `/collections/{id}/rank-file` | 3 | Rank (JD as file) |
| `GET` | `/collections/{id}/report` | 4 | Get reports |
| `GET` | `/collections/{id}/rag/status` | RAG | RAG status |
| `POST` | `/collections/{id}/rag/initialize` | RAG | Build index |
| `POST` | `/collections/{id}/rag/query` | RAG | Submit query |
| `GET` | `/rag/stream/{task_id}` | RAG | Stream response (SSE) |
| `GET` | `/health` | - | Health check |

---

## Data Flow

```
Client → Phase 1 (Upload) → Phase 2 (Process) → Phase 3 (Rank) → Phase 4 (Results + RAG)
         ↓                    ↓                   ↓                 ↓
      Extract ZIP         Extract Text        TF-IDF + Skills   View + Chat
         ↓                    ↓                   ↓                 ↓
      input/raw/          processed/          outputs/          RAG index
```

---

## Key Features

1. **4-Phase Workflow:** Upload → Process → Rank → Results
2. **OCR Support:** Automatic OCR for image-based PDFs
3. **Duplicate Detection:** SHA-256 content hashing
4. **TF-IDF Ranking:** Semantic similarity + skill matching
5. **RAG Chat:** Natural language candidate queries with LLM
6. **Real-time Streaming:** SSE for RAG responses
7. **Modern UI:** Royal Purple theme, Inter font, responsive design
8. **Comparison Mode:** Side-by-side candidate comparison
9. **Export:** JSON/CSV ranking results

---

## Tools & Dependencies

**Backend:**
- FastAPI, Pydantic
- PyPDF2, python-docx, pytesseract
- sentence-transformers, FAISS
- scikit-learn (TF-IDF)
- OpenAI, Anthropic SDKs

**Frontend:**
- Next.js 14, React, TypeScript
- Tailwind CSS
- Inter, JetBrains Mono fonts

---

## Configuration

**Environment Variables:**
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `ANTHROPIC_API_KEY` - Anthropic API key (optional)
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://127.0.0.1:8000)

**Storage:**
- Collections stored in `storage/companies/{company_id}/{collection_id}/`
- RAG index in `rag/index/`
- Query cache in `rag/cache/`

---

**Last Updated:** 2024-12-21  
**Version:** 2.0.0
