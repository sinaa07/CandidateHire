# CandidateHire - Phase 1

**Scope:** Collection ingestion, filesystem isolation, ZIP handling, metadata creation.

## Project Structure

```
resume-ranker/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI bootstrapper
│   ├── api/
│   │   ├── __init__.py
│   │   └── collections.py         # POST /collections/create
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Storage path constants
│   │   └── logger.py              # Logging setup
│   ├── services/
│   │   ├── __init__.py
│   │   └── collection_service.py  # Orchestration layer
│   └── utils/
│       ├── __init__.py
│       ├── filesystem.py          # Directory operations
│       └── zip_utils.py           # ZIP validation & extraction
├── storage/                       # Data directory (gitignored)
├── test_phase1.py                 # Integration test
└── requirements.txt
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create storage directory
mkdir storage
```

## Run

```bash
# Start server
uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Usage

### Create Collection

```bash
curl -X POST "http://localhost:8000/collections/create" \
  -F "company_id=acme_corp" \
  -F "zip_file=@resumes.zip"
```

**Response:**
```json
{
  "collection_id": "a3f7b2c1-...",
  "status": "uploaded"
}
```

### What Happens

1. Generates unique collection_id (UUID)
2. Creates directory structure:
   ```
   storage/companies/acme_corp/<collection_id>/
   ├── input/
   │   ├── raw/              # Extracted files
   │   ├── manifest/
   │   └── resumes.zip       # Original upload
   ├── processed/
   ├── artifacts/
   ├── outputs/
   ├── reports/
   └── collection_meta.json  # Metadata
   ```
3. Validates ZIP integrity
4. Extracts contents safely (prevents zip-slip)
5. Creates metadata file

### Metadata Format

`collection_meta.json`:
```json
{
  "collection_id": "uuid",
  "company_id": "company_name",
  "created_at": "2024-12-21T10:30:00",
  "status": "uploaded",
  "format": "zip_only",
  "resume_count": 0
}
```

## Test

```bash
# Run integration test
python test_phase1.py
```

## Phase 1 Constraints

✅ **In Scope:**
- ZIP upload handling
- Directory structure creation
- Metadata generation
- Safe file extraction

❌ **Out of Scope:**
- PDF/DOCX parsing
- Resume text extraction
- NLP/ML processing
- Ranking logic
- Async job processing

## Error Handling

- **400 Bad Request:** Missing company_id or invalid ZIP
- **500 Internal Error:** Filesystem errors, corrupted ZIP

## Next Phase

Phase 2 will add:
- Resume text extraction (PDF, DOCX, TXT)
- Duplicate detection
- Manifest CSV support
- Validation reports