# CandidateHire

Multi-tenant resume ranking platform with a legacy 4-phase collection workflow and a v2 company/job API.

## Tech stack

- **Backend:** FastAPI, SQLAlchemy (SQLite metadata), sentence-transformers, Hugging Face NER
- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Storage:** File-based resumes/embeddings under `storage/`; metadata in `storage/candidatehire.db`

## Quick start

### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional

# Development: skip API key checks
export DISABLE_AUTH=true

uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
export NEXT_PUBLIC_COMPANY_ID=<your-company-uuid>
export NEXT_PUBLIC_COMPANY_API_KEY=<your-api-key>
npm run dev
```

- Legacy UI: http://localhost:3000/
- v2 Dashboard: http://localhost:3000/dashboard

## First company and job

1. **Create a company** (no auth required):

```bash
curl -X POST http://127.0.0.1:8000/api/v2/companies/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "slug": "acme"}'
```

Save `id` and `api_key` from the response.

2. **Create a job** (requires `X-Company-API-Key` unless `DISABLE_AUTH=true`):

```bash
curl -X POST "http://127.0.0.1:8000/api/v2/companies/{company_id}/jobs/" \
  -H "X-Company-API-Key: {api_key}" \
  -F "title=Backend Engineer" \
  -F "jd_text=Python and FastAPI required. 3+ years experience."
```

3. **Configure the frontend** in browser console or `.env.local`:

```bash
NEXT_PUBLIC_COMPANY_ID=<company_id>
NEXT_PUBLIC_COMPANY_API_KEY=<api_key>
```

Or:

```javascript
localStorage.setItem('candidatehire_company_id', '<company_id>')
localStorage.setItem('candidatehire_api_key', '<api_key>')
```

## v2 API endpoints

All routes under `/api/v2/companies/{company_id}/…` require header `X-Company-API-Key` matching the company (except `POST /api/v2/companies/`).

### Companies

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/companies/` | Create company |
| GET | `/api/v2/companies/{company_id}` | Get company |
| PATCH | `/api/v2/companies/{company_id}/settings` | Merge settings JSON |

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/companies/{company_id}/jobs/` | Create job (multipart: title, jd_text, optional jd_file) |
| GET | `/api/v2/companies/{company_id}/jobs/` | List jobs |
| GET | `/api/v2/companies/{company_id}/jobs/{job_id}` | Job detail |
| PATCH | `/api/v2/companies/{company_id}/jobs/{job_id}` | Update job |
| DELETE | `/api/v2/companies/{company_id}/jobs/{job_id}` | Soft delete job |

### Resumes

| Method | Path | Description |
|--------|------|-------------|
| POST | `…/jobs/{job_id}/resumes/` | Upload files or ZIP |
| GET | `…/jobs/{job_id}/resumes/` | List candidates |
| DELETE | `…/jobs/{job_id}/resumes/{candidate_id}` | Delete candidate + files |

### Pipeline

| Method | Path | Description |
|--------|------|-------------|
| POST | `…/jobs/{job_id}/pipeline/index` | Queue background indexing |
| GET | `…/jobs/{job_id}/pipeline/status` | Indexing status counts |
| POST | `…/jobs/{job_id}/pipeline/rank` | Run ranking |
| POST | `…/jobs/{job_id}/pipeline/rerank` | Rerank in memory (new weights) |
| GET | `…/jobs/{job_id}/pipeline/rankings` | Paginated rankings |
| GET | `…/jobs/{job_id}/pipeline/rankings/export` | CSV export |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/companies/{company_id}/dashboard` | Company summary + job cards |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/health/models` | MiniLM / NER load status |

## Legacy collections API

Unchanged under `/collections/*` (upload → process → rank → report + RAG).

## Environment variables

| Variable | Description |
|----------|-------------|
| `DISABLE_AUTH` | `true` to skip `X-Company-API-Key` validation (development only) |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend (default `http://127.0.0.1:8000`) |
| `NEXT_PUBLIC_COMPANY_ID` | Default company UUID for v2 dashboard |
| `NEXT_PUBLIC_COMPANY_API_KEY` | API key for v2 frontend requests |
| `CORS_ORIGINS` | Extra comma-separated CORS origins |
| `SMOKE_TEST_URL` | Base URL for smoke test (default `http://127.0.0.1:8000`) |
| `SMOKE_INDEX_TIMEOUT` | Indexing poll timeout seconds (default `120`) |

## Smoke test

With the API running (models load on first request; pre-warm via startup):

```bash
export DISABLE_AUTH=true
uvicorn app.main:app --reload

# another terminal
python scripts/smoke_test.py
```

The script:

1. Creates a company  
2. Creates a job with sample JD  
3. Uploads 3 resumes from `scripts/test_resumes/`  
4. Triggers indexing and polls until complete  
5. Runs ranking and validates results  
6. Reranks with equal weights  
7. Checks dashboard counts  

Prints **PASS/FAIL** and response time per step.

## Project layout

```
app/
  api/deps.py          # get_verified_company auth dependency
  api/routes/v2/       # v2 routers
  db/session.py        # SessionLocal, get_db()
  models/              # SQLAlchemy ORM + Pydantic schemas
  services/v2/         # indexing, ranking, reranking
frontend/
  app/dashboard/       # v2 dashboard
  app/jobs/            # job detail + rankings
scripts/
  smoke_test.py
  test_resumes/        # sample .txt resumes
storage/
  candidatehire.db
  companies/{company_id}/jobs/{job_id}/...
```
