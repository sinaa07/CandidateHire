# CandidateHire - Project Documentation

## Overview

CandidateHire is a resume processing and ranking system that follows a 4-phase workflow to process resume collections and rank them against job descriptions. The system is built with FastAPI (backend) and Next.js (frontend), with a modular architecture designed for easy extension.

## Architecture

### Project Structure

```
hire/
├── app/                          # Backend application
│   ├── main.py                  # FastAPI app & CORS setup
│   ├── api/
│   │   └── routes/              # API route handlers
│   │       ├── collections_create.py    # Phase 1
│   │       ├── collections_process.py  # Phase 2
│   │       ├── collections_rank.py     # Phase 3
│   │       ├── collections_rank_file.py # Phase 3 (file upload variant)
│   │       └── collections_report.py   # Phase 4
│   ├── core/
│   │   ├── config.py            # Storage paths & configuration
│   │   ├── errors.py            # Error handling utilities
│   │   └── logger.py            # Logging setup
│   ├── models/
│   │   ├── api_schemas.py       # Pydantic request/response models
│   │   └── enums.py             # Status enums
│   ├── services/                # Business logic layer
│   │   ├── collection_service.py    # Phase 1 orchestration
│   │   ├── processing_service.py    # Phase 2 orchestration
│   │   └── ranking_service.py       # Phase 3 orchestration
│   └── utils/                   # Utility functions
│       ├── artifacts.py         # ML artifact management
│       ├── filesystem.py        # Directory operations
│       ├── hashing.py           # SHA-256 for duplicates
│       ├── io_reports.py        # Report file I/O
│       ├── jd_io.py             # Job description I/O
│       ├── paths.py             # Path resolution utilities
│       ├── scoring.py           # Ranking score calculation
│       ├── skills.py            # Skill extraction & matching
│       ├── text_extraction.py   # PDF/DOCX/TXT extraction
│       ├── validation.py        # Text validation
│       ├── vectorization.py     # TF-IDF vectorization
│       └── zip_utils.py         # ZIP validation & extraction
├── frontend/                     # Next.js frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── phases/          # Phase UI components
│   │   ├── contexts/
│   │   │   └── AppContext.tsx   # Global state management
│   │   ├── utils/
│   │   │   └── api.ts           # API client functions
│   │   └── types/
│   │       └── index.ts         # TypeScript types
│   └── app/                     # Next.js app directory
└── storage/                     # Data directory (gitignored)
    └── companies/
        └── {company_id}/
            └── {collection_id}/
                ├── input/
                │   ├── raw/              # Extracted ZIP contents
                │   └── jd.txt/.pdf/.docx # Job description
                ├── processed/            # Extracted text files (.txt)
                ├── artifacts/            # ML artifacts (vectorizer, matrix)
                ├── outputs/              # Ranking results (JSON, CSV)
                ├── reports/              # Processing & ranking reports
                └── collection_meta.json  # Collection metadata
```

---

## 4-Phase Workflow

### Phase 1: Collection Creation (Upload)

**Purpose:** Upload and extract resume ZIP files

**API Route:** `POST /collections/create`

**Request:**
```json
{
  "company_id": "acme_corp",
  "zip_file": <multipart/form-data>
}
```

**Response:**
```json
{
  "status": "uploaded",
  "collection_id": "uuid-string",
  "company_id": "acme_corp"
}
```

**Process:**
1. Generate unique `collection_id` (UUID)
2. Create directory structure under `storage/companies/{company_id}/{collection_id}/`
3. Save uploaded ZIP temporarily
4. Extract ZIP contents to `input/raw/` (filters out macOS resource forks)
5. Create `collection_meta.json` with metadata
6. Return collection ID

**Key Files:**
- Route: `app/api/routes/collections_create.py`
- Service: `app/services/collection_service.py` (if used)
- Utils: `app/utils/zip_utils.py`

**Output:**
- Directory structure created
- Files extracted to `input/raw/`
- Metadata file created

---

### Phase 2: Processing (Text Extraction & Validation)

**Purpose:** Extract text from resumes, validate, and detect duplicates

**API Route:** `POST /collections/{collection_id}/process`

**Request:**
```json
{
  "company_id": "acme_corp"
}
```

**Response:**
```json
{
  "status": "completed",
  "collection_id": "uuid-string",
  "details": {
    "status": "completed",
    "stats": {
      "total_files": 236,
      "ok": 118,
      "failed": 0,
      "empty": 0,
      "duplicate": 0
    },
    "reports_generated": ["validation_report.json", "duplicate_report.json"]
  }
}
```

**Process:**
1. Read all files from `input/raw/` (recursively)
2. Filter out metadata files (`._*`, `.DS_Store`, etc.)
3. For each resume file:
   - Extract text (PDF/DOCX/TXT)
     - **PDFs**: Regular extraction first, OCR fallback if text < threshold (100 chars)
     - **DOCX/TXT**: Direct extraction
   - Validate text (not empty/whitespace)
   - Compute SHA-256 hash for duplicate detection
   - Save extracted text to `processed/{filename}.txt`
4. Generate reports:
   - `reports/validation_report.json` - Processing stats & file statuses
   - `reports/duplicate_report.json` - Duplicate file mappings
5. Update `collection_meta.json` with processing status

**Key Files:**
- Route: `app/api/routes/collections_process.py`
- Service: `app/services/processing_service.py`
- Utils:
  - `app/utils/text_extraction.py` - PDF/DOCX/TXT extraction (with OCR fallback)
  - `app/utils/ocr_extraction.py` - OCR functionality for image-based PDFs
  - `app/utils/validation.py` - Text validation
  - `app/utils/hashing.py` - SHA-256 hashing

**OCR Integration:**
- Automatically uses OCR for image-based PDFs when regular extraction yields < 100 characters
- No code changes needed - fully integrated into Phase 2
- See `OCR_SETUP.md` for installation and configuration

**Output:**
- Extracted text files in `processed/`
- Validation report with stats
- Duplicate report
- Updated metadata

---

### Phase 3: Ranking (Resume Scoring)

**Purpose:** Rank resumes against a job description using TF-IDF and skill matching

**API Routes:**
- `POST /collections/{collection_id}/rank` - JD as text
- `POST /collections/{collection_id}/rank-file` - JD as file upload

**Request (text):**
```json
{
  "company_id": "acme_corp",
  "jd_text": "We are looking for a software engineer...",
  "top_k": 10  // optional
}
```

**Request (file):**
```
FormData:
  - company_id: "acme_corp"
  - jd_file: <PDF/DOCX/TXT file>
  - top_k: 10  // optional
```

**Response:**
```json
{
  "status": "completed",
  "collection_id": "uuid-string",
  "details": {
    "status": "completed",
    "resume_count": 118,
    "ranked_count": 118,
    "top_k": 10,
    "outputs_generated": ["ranking_results.json", "ranking_results.csv"],
    "jd_saved_as": "jd.pdf"  // if file upload
  }
}
```

**Process:**
1. Validate collection has processed resumes
2. Extract JD text (from input or file)
3. Save JD to `input/jd.{ext}`
4. Load processed resume texts from `processed/`
5. Build TF-IDF vectorizer and fit on resumes
6. For each resume:
   - Compute TF-IDF cosine similarity with JD
   - Extract skills from resume and JD
   - Calculate skill overlap score
   - Combine scores (TF-IDF + skills)
7. Sort by final score (descending)
8. Apply `top_k` filter if specified
9. Generate outputs:
   - `outputs/ranking_results.json` - Full ranking with scores
   - `outputs/ranking_results.csv` - CSV export
   - `reports/ranking_summary.json` - Summary stats
10. Save ML artifacts:
    - `artifacts/tfidf_vectorizer.pkl`
    - `artifacts/resume_matrix.npz`
    - `artifacts/resume_index.json`

**Key Files:**
- Routes: 
  - `app/api/routes/collections_rank.py`
  - `app/api/routes/collections_rank_file.py`
- Service: `app/services/ranking_service.py`
- Utils:
  - `app/utils/vectorization.py` - TF-IDF vectorization
  - `app/utils/skills.py` - Skill extraction & matching
  - `app/utils/scoring.py` - Score combination
  - `app/utils/jd_io.py` - JD file handling
  - `app/utils/artifacts.py` - ML artifact management

**Output:**
- Ranking results (JSON & CSV)
- Ranking summary report
- ML artifacts for potential reuse

---

### Phase 4: Reports (Results Retrieval)

**Purpose:** Retrieve processing and ranking results

**API Routes:**
- `GET /collections/{collection_id}/report` - Full report
- `GET /collections/{collection_id}/outputs` - Output file availability

**Request:**
```
GET /collections/{collection_id}/report?company_id=acme_corp&include_results=true
```

**Response:**
```json
{
  "collection_id": "uuid-string",
  "company_id": "acme_corp",
  "meta": { /* collection metadata */ },
  "phase2": {
    "validation_report": {
      "total_files": 236,
      "ok": 118,
      "failed": 0,
      "empty": 0,
      "duplicate": 0,
      "files": [ /* file statuses */ ]
    },
    "duplicate_report": {
      "duplicates": [ /* duplicate mappings */ ]
    }
  },
  "phase3": {
    "ranking_summary": {
      "resume_count": 118,
      "ranked_count": 118,
      "top_k": 10
    },
    "ranking_results": [ /* full ranking results if include_results=true */ ]
  }
}
```

**Key Files:**
- Route: `app/api/routes/collections_report.py`
- Utils: `app/utils/io_reports.py`

---

## API Routes Summary

| Method | Route | Phase | Description |
|--------|-------|-------|-------------|
| `POST` | `/collections/create` | 1 | Upload ZIP file, create collection |
| `POST` | `/collections/{id}/process` | 2 | Process resumes (extract, validate) |
| `POST` | `/collections/{id}/rank` | 3 | Rank resumes (JD as text) |
| `POST` | `/collections/{id}/rank-file` | 3 | Rank resumes (JD as file) |
| `GET` | `/collections/{id}/report` | 4 | Get processing & ranking reports |
| `GET` | `/collections/{id}/outputs` | 4 | Check output file availability |
| `GET` | `/health` | - | Health check |
| `GET` | `/` | - | API info |

---

## Extension Points: Adding Features Between Phases

The architecture is designed with clear separation of concerns, making it easy to add features between phases. Here's how:

### 1. Adding a New Phase

**Example: Add Phase 2.5 - Resume Enrichment**

1. **Create Service:**
   ```python
   # app/services/enrichment_service.py
   def enrich_collection(company_id: str, collection_id: str) -> dict:
       # Your enrichment logic
       pass
   ```

2. **Create Route:**
   ```python
   # app/api/routes/collections_enrich.py
   @router.post("/{collection_id}/enrich")
   async def enrich_collection_endpoint(...):
       result = enrich_collection(...)
       return StandardResponse(...)
   ```

3. **Register Route:**
   ```python
   # app/main.py
   from app.api.routes import collections_enrich
   app.include_router(collections_enrich.router)
   ```

4. **Update Frontend:**
   - Add new phase component in `frontend/src/components/phases/`
   - Add API function in `frontend/src/utils/api.ts`
   - Update phase flow in `AppContext`

### 2. Adding Features Within a Phase

**Example: Add OCR Support to Phase 2**

1. **Extend Text Extraction:**
   ```python
   # app/utils/text_extraction.py
   def _extract_pdf_with_ocr(file_path: Path) -> str:
       # Try regular extraction first
       text = _extract_pdf(file_path)
       if not text or len(text) < 50:
           # Fallback to OCR
           return _extract_with_ocr(file_path)
       return text
   ```

2. **Update Processing Service:**
   ```python
   # app/services/processing_service.py
   # Modify the extraction call to use OCR fallback
   ```

### 3. Adding Pre/Post Processing Hooks

**Example: Add Pre-Processing Validation**

1. **Create Hook Function:**
   ```python
   # app/utils/hooks.py
   def pre_process_hook(collection_root: Path) -> dict:
       # Validate file formats, sizes, etc.
       return {"valid": True, "warnings": []}
   ```

2. **Integrate in Route:**
   ```python
   # app/api/routes/collections_process.py
   from app.utils.hooks import pre_process_hook
   
   @router.post("/{collection_id}/process")
   async def process_collection_endpoint(...):
       # Run pre-processing hook
       validation = pre_process_hook(collection_root)
       if not validation["valid"]:
           raise ValueError("Pre-processing validation failed")
       
       # Continue with normal processing
       result = process_collection(...)
   ```

### 4. Adding New File Formats

**Example: Add RTF Support**

1. **Extend Text Extraction:**
   ```python
   # app/utils/text_extraction.py
   def extract_text(file_path: Path) -> str:
       suffix = file_path.suffix.lower()
       if suffix == '.rtf':
           return _extract_rtf(file_path)
       # ... existing code
   ```

2. **Update File Filtering:**
   ```python
   # app/services/processing_service.py
   resume_files = [
       f for f in resume_files 
       if f.suffix.lower() in ['.pdf', '.docx', '.txt', '.rtf']  # Add .rtf
   ]
   ```

### 5. Adding New Scoring Methods

**Example: Add Experience-Based Scoring**

1. **Create Scoring Utility:**
   ```python
   # app/utils/experience_scoring.py
   def extract_experience(text: str) -> float:
       # Extract years of experience
       pass
   
   def experience_score(jd_years: int, resume_years: int) -> float:
       # Calculate score
       pass
   ```

2. **Integrate in Ranking Service:**
   ```python
   # app/services/ranking_service.py
   from app.utils.experience_scoring import extract_experience, experience_score
   
   # In ranking loop:
   resume_exp = extract_experience(resume_text)
   jd_exp = extract_experience(jd_text)
   exp_score = experience_score(jd_exp, resume_exp)
   
   # Combine with existing scores
   final_score = combine_scores(tfidf_score, skill_score, exp_score)
   ```

### 6. Adding Data Validation Between Phases

**Example: Validate Phase 2 Output Before Phase 3**

1. **Create Validation Function:**
   ```python
   # app/utils/phase_validation.py
   def validate_phase2_complete(collection_root: Path) -> bool:
       processed_dir = collection_root / "processed"
       reports_dir = collection_root / "reports"
       
       has_files = list(processed_dir.glob("*.txt"))
       has_report = (reports_dir / "validation_report.json").exists()
       
       return len(has_files) > 0 and has_report
   ```

2. **Add to Phase 3 Route:**
   ```python
   # app/api/routes/collections_rank.py
   from app.utils.phase_validation import validate_phase2_complete
   
   if not validate_phase2_complete(collection_root):
       raise ValueError("Phase 2 not completed. Run processing first.")
   ```

---

## Data Flow Diagram

```
┌─────────────┐
│   Client   │
└─────┬──────┘
      │
      │ POST /collections/create
      ▼
┌─────────────────────┐
│  Phase 1: Create    │
│  - Extract ZIP      │
│  - Create structure │
└─────┬───────────────┘
      │
      │ Files in input/raw/
      ▼
┌─────────────────────┐
│  Phase 2: Process   │
│  - Extract text     │
│  - Validate         │
│  - Detect dupes     │
└─────┬───────────────┘
      │
      │ Text files in processed/
      ▼
┌─────────────────────┐
│  Phase 3: Rank       │
│  - Vectorize         │
│  - Score & rank      │
└─────┬───────────────┘
      │
      │ Results in outputs/
      ▼
┌─────────────────────┐
│  Phase 4: Report     │
│  - Retrieve results │
└─────────────────────┘
```

---

## Key Design Principles

1. **Separation of Concerns:**
   - Routes handle HTTP requests/responses
   - Services contain business logic
   - Utils provide reusable functions

2. **Stateless Operations:**
   - Each phase can be run independently (with prerequisites)
   - State stored in filesystem, not memory

3. **Idempotency:**
   - Re-running a phase should be safe
   - Services check for existing outputs

4. **Extensibility:**
   - New phases can be added without modifying existing code
   - Utils can be extended with new functions
   - Services can be composed with new features

5. **Error Handling:**
   - Consistent error format via `to_http_error()`
   - Detailed error messages in validation reports
   - Graceful degradation where possible

---

## Common Extension Patterns

### Pattern 1: Middleware Between Phases
```python
# app/utils/middleware.py
def phase_middleware(phase_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Pre-execution logic
            validate_prerequisites(...)
            # Execute phase
            result = func(*args, **kwargs)
            # Post-execution logic
            update_metadata(...)
            return result
        return wrapper
    return decorator
```

### Pattern 2: Plugin System
```python
# app/core/plugins.py
PLUGINS = []

def register_plugin(plugin):
    PLUGINS.append(plugin)

def run_plugins(hook_name, *args, **kwargs):
    for plugin in PLUGINS:
        if hasattr(plugin, hook_name):
            getattr(plugin, hook_name)(*args, **kwargs)
```

### Pattern 3: Event-Driven Extensions
```python
# app/core/events.py
from typing import Callable, List

EVENT_HANDLERS = {
    'phase2.complete': [],
    'phase3.complete': [],
}

def on_event(event_name: str, handler: Callable):
    EVENT_HANDLERS[event_name].append(handler)

def emit_event(event_name: str, *args, **kwargs):
    for handler in EVENT_HANDLERS[event_name]:
        handler(*args, **kwargs)
```

---

## Testing New Features

When adding features, follow the existing test structure:

```python
# tests/test_new_feature.py
def test_new_feature_success(client, created_collection_id, company_id):
    # Test the new feature
    response = client.post(f"/collections/{created_collection_id}/new-feature", ...)
    assert response.status_code == 200
    # Verify outputs
```

---

## Configuration

Key configuration in `app/core/config.py`:
- `COLLECTIONS_ROOT` - Base path for collections
- Storage paths are relative to project root

To change storage location, modify `config.py` or use environment variables.

---

## Next Steps for Extension

1. **Identify insertion point:** Which phase needs extension?
2. **Create utility functions:** Add reusable logic to `app/utils/`
3. **Create/update service:** Add business logic to appropriate service
4. **Create/update route:** Add API endpoint if needed
5. **Update frontend:** Add UI components if user-facing
6. **Add tests:** Ensure new features are tested
7. **Update documentation:** Document new features

---

## Support & Questions

For questions about extending the system:
1. Review existing phase implementations as examples
2. Check utility functions for reusable patterns
3. Follow the separation of concerns principle
4. Maintain consistency with existing error handling

---

**Last Updated:** 2024-12-21
**Version:** 1.0.0

