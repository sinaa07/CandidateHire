# CandidateHire

An AI-powered resume processing and ranking system that processes resume collections and ranks them against job descriptions. The system features a comprehensive 4-phase workflow with an integrated RAG (Retrieval-Augmented Generation) chat interface for natural language candidate queries.

## Overview

CandidateHire is designed to streamline the resume screening process by automating text extraction, validation, ranking, and candidate discovery. The system processes resume collections through a structured workflow and provides an intelligent chat interface to query candidates using natural language.

### Key Features

- **4-Phase Workflow**: Upload → Process → Rank → Results & Chat
- **Multi-Format Support**: PDF, DOCX, TXT with automatic OCR for image-based PDFs
- **Intelligent Ranking**: TF-IDF semantic similarity combined with skill matching
- **RAG Chat Interface**: Natural language queries to find candidates ("Find Python developers with 5+ years experience")
- **Real-time Streaming**: Server-Sent Events (SSE) for live RAG responses
- **Duplicate Detection**: SHA-256 content hashing to identify duplicate resumes
- **Comparison Mode**: Side-by-side candidate comparison
- **Export Capabilities**: JSON and CSV export of ranking results
- **Modern UI**: Responsive web interface with Royal Purple theme

## Tech Stack

**Backend:**
- FastAPI (Python)
- sentence-transformers for embeddings
- FAISS for vector search
- scikit-learn for TF-IDF
- PyPDF2, python-docx, pytesseract for text extraction
- OpenAI/Anthropic for LLM integration

**Frontend:**
- Next.js 14 (TypeScript, React)
- Tailwind CSS
- Inter font family

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- npm, yarn, or pnpm
- Tesseract OCR (for image-based PDF processing)

### Installing Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download and install from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)

## Setup

### Backend Setup

1. **Create a virtual environment:**
```bash
python -m venv venv
```

2. **Activate the virtual environment:**
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

4. **Download spaCy language model (for NER):**
```bash
python -m spacy download en_core_web_sm
```

5. **Create storage directory:**
```bash
mkdir -p storage
```

6. **Set up environment variables (optional):**
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. **Set up environment variables (optional):**
Create a `.env.local` file in the frontend directory:
```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Running the Project

### Start Backend Server

From the project root directory:

```bash
uvicorn app.main:app --reload
```

The API server will run at `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Start Frontend Development Server

From the frontend directory:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

The frontend will run at `http://localhost:3000`

## Project Structure

```
hire/
├── app/                          # Backend application
│   ├── main.py                  # FastAPI app entry point
│   ├── api/routes/              # API route handlers
│   ├── services/                # Business logic layer
│   ├── utils/                   # Utilities (embeddings, OCR, etc.)
│   └── models/                  # Pydantic schemas
├── frontend/                     # Next.js frontend
│   ├── src/components/          # React components
│   ├── contexts/                # React contexts
│   └── utils/                   # Frontend utilities
└── storage/                      # Data directory (gitignored)
    └── companies/{company_id}/{collection_id}/
```

## Workflow Overview

### Phase 1: Collection Creation
Upload resume collections as ZIP files. The system extracts files and creates a structured directory with metadata.

### Phase 2: Processing
Extract text from resumes (PDF, DOCX, TXT), validate content, and detect duplicates using content hashing.

### Phase 3: Ranking
Rank resumes against a job description using TF-IDF semantic similarity (70%) and skill matching (30%).

### Phase 4: Results & RAG Chat
View ranking results in a dashboard, compare candidates side-by-side, and query candidates using natural language through the RAG chat interface.

## API Endpoints

- `POST /collections/create` - Upload and create collection
- `POST /collections/{id}/process` - Process resumes
- `POST /collections/{id}/rank` - Rank resumes (JD as text)
- `POST /collections/{id}/rank-file` - Rank resumes (JD as file)
- `GET /collections/{id}/report` - Get processing and ranking reports
- `GET /collections/{id}/rag/status` - Check RAG system status
- `POST /collections/{id}/rag/query` - Submit natural language query
- `GET /rag/stream/{task_id}` - Stream RAG response (SSE)
- `POST /collections/{id}/rag/evaluate` - Evaluate RAG system
- `GET /health` - Health check

## Testing

Run backend tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=app
```

## Documentation

- `PROJECT_DOCUMENTATION.md` - Comprehensive project documentation
- `API_DOCUMENTATION.md` - Detailed API reference
- `OCR_SETUP.md` - OCR configuration guide
- `RAG_IMPLEMENTATION.md` - RAG system architecture
- `PERFORMANCE_ANALYSIS.md` - Performance metrics and analysis

## License

This project is private and proprietary.

## Version

2.0.0
