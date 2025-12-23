# CandidateHire API - Frontend Integration Guide

## Overview

The CandidateHire API is a RESTful service for processing and ranking resume collections. The API follows a 4-phase workflow:

1. **Phase 1: Create Collection** - Upload resumes as a ZIP file
2. **Phase 2: Process Collection** - Extract text, validate, and detect duplicates
3. **Phase 3: Rank Collection** - Rank resumes against a job description
4. **Phase 4: Reports** - Retrieve processing and ranking results

## Base URL

```
http://localhost:8000  (default development)
```

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Common Response Format

### Success Response

Most endpoints return a `StandardResponse` format:

```json
{
  "status": "completed",
  "collection_id": "uuid-string",
  "details": {
    // Endpoint-specific data
  }
}
```

### Error Response

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid input or validation error
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Root Endpoint

**GET** `/`

Get API information and available endpoints.

**Response:**
```json
{
  "service": "CandidateHire API",
  "version": "1.0.0",
  "endpoints": {
    "create": "/collections/create (POST)",
    "process": "/collections/{id}/process (POST)",
    "rank": "/collections/{id}/rank (POST)",
    "report": "/collections/{id}/report (GET)",
    "outputs": "/collections/{id}/outputs (GET)"
  }
}
```

---

## Phase 1: Create Collection

### POST `/collections/create`

Upload a ZIP file containing resumes to create a new collection.

**Content-Type:** `multipart/form-data`

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | string (form field) | Yes | Company identifier (e.g., "acme", "techcorp") |
| `zip_file` | file (form field) | Yes | ZIP file containing resume files (.pdf, .docx, .txt) |

**Request Example (JavaScript/Fetch):**
```javascript
const formData = new FormData();
formData.append('company_id', 'acme');
formData.append('zip_file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/collections/create', {
  method: 'POST',
  body: formData
});
```

**Request Example (cURL):**
```bash
curl -X POST "http://localhost:8000/collections/create" \
  -F "company_id=acme" \
  -F "zip_file=@resumes.zip"
```

**Success Response (200):**
```json
{
  "status": "uploaded",
  "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
  "company_id": "acme"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid ZIP file or empty ZIP
  ```json
  {
    "detail": "Invalid ZIP file"
  }
  ```

- `400 Bad Request` - Missing required fields
  ```json
  {
    "detail": "Field required"
  }
  ```

**Important Notes:**
- The ZIP file must contain at least one valid resume file
- Supported file formats: `.pdf`, `.docx`, `.txt`
- The `collection_id` returned is a UUID that must be stored for subsequent operations

---

## Phase 2: Process Collection

### POST `/collections/{collection_id}/process`

Process all resumes in a collection: extract text, validate content, and detect duplicates.

**Content-Type:** `application/json`

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | string (path) | Yes | Collection UUID from Phase 1 |

**Request Body:**
```json
{
  "company_id": "acme"
}
```

**Request Example (JavaScript/Fetch):**
```javascript
const response = await fetch(
  `http://localhost:8000/collections/${collectionId}/process`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      company_id: 'acme'
    })
  }
);
```

**Success Response (200):**
```json
{
  "status": "completed",
  "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
  "details": {
    "status": "completed",
    "stats": {
      "total_files": 10,
      "ok": 7,
      "failed": 1,
      "empty": 1,
      "duplicate": 1
    },
    "reports_generated": [
      "validation_report.json",
      "duplicate_report.json"
    ]
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `details.stats.total_files` | integer | Total number of files processed |
| `details.stats.ok` | integer | Number of successfully processed resumes |
| `details.stats.failed` | integer | Number of files that failed text extraction |
| `details.stats.empty` | integer | Number of empty/invalid resumes |
| `details.stats.duplicate` | integer | Number of duplicate resumes detected |

**Error Responses:**

- `400 Bad Request` - No resume files found
  ```json
  {
    "detail": "No resume files found in collection"
  }
  ```

- `404 Not Found` - Collection not found
  ```json
  {
    "detail": "Collection not found"
  }
  ```

**Important Notes:**
- Must be called after Phase 1 (Create Collection)
- Processing status is saved to `collection_meta.json`
- Validation and duplicate reports are generated and can be retrieved via Phase 4

---

## Phase 3: Rank Collection

### POST `/collections/{collection_id}/rank`

Rank processed resumes against a job description using TF-IDF and skill matching.

**Content-Type:** `application/json`

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | string (path) | Yes | Collection UUID from Phase 1 |

**Request Body:**
```json
{
  "company_id": "acme",
  "jd_text": "We are looking for a software engineer with Python and JavaScript experience...",
  "top_k": 5
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_id` | string | Yes | Company identifier |
| `jd_text` | string | Yes | Job description text (must be non-empty) |
| `top_k` | integer | No | Limit results to top N resumes (must be >= 1) |

**Request Example (JavaScript/Fetch):**
```javascript
const response = await fetch(
  `http://localhost:8000/collections/${collectionId}/rank`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      company_id: 'acme',
      jd_text: 'We are looking for a software engineer...',
      top_k: 10  // Optional: limit to top 10 results
    })
  }
);
```

**Success Response (200):**
```json
{
  "status": "completed",
  "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
  "details": {
    "status": "completed",
    "resume_count": 7,
    "ranked_count": 7,
    "top_k": null,
    "outputs_generated": [
      "ranking_results.json",
      "ranking_results.csv",
      "ranking_summary.json"
    ]
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `details.resume_count` | integer | Total number of resumes ranked |
| `details.ranked_count` | integer | Number of resumes in results (may differ if `top_k` is set) |
| `details.top_k` | integer \| null | Top K limit applied (null if not specified) |
| `details.outputs_generated` | array | List of generated output files |

**Error Responses:**

- `400 Bad Request` - Collection not processed yet
  ```json
  {
    "detail": "Run processing first - no processed resumes found"
  }
  ```

- `400 Bad Request` - Empty job description
  ```json
  {
    "detail": "jd_text must be non-empty"
  }
  ```

- `400 Bad Request` - Invalid top_k value
  ```json
  {
    "detail": "top_k must be >= 1"
  }
  ```

- `404 Not Found` - Collection not found
  ```json
  {
    "detail": "Collection not found"
  }
  ```

**Important Notes:**
- Must be called after Phase 2 (Process Collection)
- Ranking uses TF-IDF (70% weight) and skill matching (30% weight)
- Results are sorted by final score (descending)
- Ranking results are saved as JSON and CSV files

---

## Phase 4: Reports

### GET `/collections/{collection_id}/report`

Retrieve aggregated reports for a collection, including validation, duplicates, and ranking summaries.

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | string (path) | Yes | Collection UUID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `company_id` | string | Yes | - | Company identifier |
| `include_results` | boolean | No | `false` | Include full ranking results array |

**Request Example (JavaScript/Fetch):**
```javascript
// Get summary only
const response = await fetch(
  `http://localhost:8000/collections/${collectionId}/report?company_id=acme`
);

// Get summary + full ranking results
const responseWithResults = await fetch(
  `http://localhost:8000/collections/${collectionId}/report?company_id=acme&include_results=true`
);
```

**Success Response (200) - Summary Only:**
```json
{
  "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
  "company_id": "acme",
  "meta": {
    "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
    "company_id": "acme",
    "created_at": "2024-12-21T10:30:00.000000+00:00",
    "upload_status": "uploaded",
    "processing_status": "completed",
    "processed_at": "2024-12-21T10:35:00.000000+00:00",
    "ranking_status": "completed",
    "ranked_at": "2024-12-21T10:40:00.000000+00:00"
  },
  "phase2": {
    "validation_report": {
      "total_files": 10,
      "ok": 7,
      "failed": 1,
      "empty": 1,
      "duplicate": 1,
      "files": [
        {
          "filename": "resume1.pdf",
          "status": "OK",
          "reason": null
        },
        {
          "filename": "resume2.pdf",
          "status": "EMPTY",
          "reason": "No extractable text"
        },
        {
          "filename": "resume3.pdf",
          "status": "DUPLICATE",
          "reason": "Duplicate of resume1.pdf"
        },
        {
          "filename": "resume4.pdf",
          "status": "FAILED",
          "reason": "Text extraction failed"
        }
      ]
    },
    "duplicate_report": {
      "duplicates": [
        {
          "filename": "resume3.pdf",
          "duplicate_of": "resume1.pdf"
        }
      ]
    }
  },
  "phase3": {
    "ranking_summary": {
      "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
      "company_id": "acme",
      "ranked_at": "2024-12-21T10:40:00.000000+00:00",
      "resume_count": 7,
      "ranked_count": 7,
      "weights": {
        "tfidf": 0.7,
        "skill": 0.3
      },
      "top_k": null
    }
  }
}
```

**Success Response (200) - With Results (`include_results=true`):**
```json
{
  "collection_id": "3e162a2c-a0c4-4ea7-ae2b-aeaafc08a8cd",
  "company_id": "acme",
  "meta": { /* ... same as above ... */ },
  "phase2": { /* ... same as above ... */ },
  "phase3": {
    "ranking_summary": { /* ... same as above ... */ },
    "ranking_results": [
      {
        "rank": 1,
        "filename": "resume1.pdf.txt",
        "tfidf_score": 0.8542,
        "skill_score": 0.7500,
        "final_score": 0.8229,
        "explainability": {
          "matched_skills": ["Python", "JavaScript", "React"],
          "missing_skills": ["Docker", "Kubernetes"]
        }
      },
      {
        "rank": 2,
        "filename": "resume2.pdf.txt",
        "tfidf_score": 0.7234,
        "skill_score": 0.6000,
        "final_score": 0.6834,
        "explainability": {
          "matched_skills": ["Python", "Django"],
          "missing_skills": ["React", "TypeScript", "Docker"]
        }
      }
    ]
  }
}
```

**Response Structure:**

| Field | Type | Description |
|-------|------|-------------|
| `meta` | object \| null | Collection metadata (null if not available) |
| `phase2.validation_report` | object \| null | Processing validation report (null if Phase 2 not completed) |
| `phase2.duplicate_report` | object \| null | Duplicate detection report (null if Phase 2 not completed) |
| `phase3.ranking_summary` | object \| null | Ranking summary (null if Phase 3 not completed) |
| `phase3.ranking_results` | array \| null | Full ranking results (only if `include_results=true`) |

**Validation Report Structure:**

```typescript
{
  total_files: number;
  ok: number;
  failed: number;
  empty: number;
  duplicate: number;
  files: Array<{
    filename: string;
    status: "OK" | "FAILED" | "EMPTY" | "DUPLICATE";
    reason: string | null;
  }>;
}
```

**Duplicate Report Structure:**

```typescript
{
  duplicates: Array<{
    filename: string;
    duplicate_of: string;
  }>;
}
```

**Ranking Summary Structure:**

```typescript
{
  collection_id: string;
  company_id: string;
  ranked_at: string;  // ISO 8601 datetime
  resume_count: number;
  ranked_count: number;
  weights: {
    tfidf: number;  // 0.7
    skill: number;  // 0.3
  };
  top_k: number | null;
}
```

**Ranking Result Item Structure:**

```typescript
{
  rank: number;  // 1-based ranking
  filename: string;  // Processed filename (usually .txt extension)
  tfidf_score: number;  // TF-IDF similarity score (0-1)
  skill_score: number;  // Skill overlap score (0-1)
  final_score: number;  // Combined score (0-1)
  explainability: {
    matched_skills: string[];  // Skills found in both JD and resume
    missing_skills: string[];  // Skills in JD but not in resume
  };
}
```

**Error Responses:**

- `404 Not Found` - Collection not found
  ```json
  {
    "detail": "Collection not found"
  }
  ```

**Important Notes:**
- Reports are only available after the respective phase is completed
- Missing reports will be `null` in the response
- Use `include_results=true` to get the full ranking results array (can be large)

---

### GET `/collections/{collection_id}/outputs`

Check which output files are available for download.

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | string (path) | Yes | Collection UUID |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_id` | string | Yes | Company identifier |

**Request Example (JavaScript/Fetch):**
```javascript
const response = await fetch(
  `http://localhost:8000/collections/${collectionId}/outputs?company_id=acme`
);
```

**Success Response (200):**
```json
{
  "outputs": {
    "ranking_results.json": true,
    "ranking_results.csv": true
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `outputs.ranking_results.json` | boolean | Whether JSON ranking results file exists |
| `outputs.ranking_results.csv` | boolean | Whether CSV ranking results file exists |

**Error Responses:**

- `404 Not Found` - Collection not found
  ```json
  {
    "detail": "Collection not found"
  }
  ```

**Important Notes:**
- Output files are only available after Phase 3 (Rank Collection) is completed
- Files are stored server-side and not directly downloadable via this endpoint
- Use this endpoint to check availability before attempting to download files

---

## Data Types and Enums

### Resume Status

Resume processing status values:

- `"OK"` - Successfully processed
- `"FAILED"` - Text extraction failed
- `"EMPTY"` - No extractable text found
- `"DUPLICATE"` - Duplicate of another resume

### Score Ranges

- **TF-IDF Score**: `0.0` to `1.0` (cosine similarity)
- **Skill Score**: `0.0` to `1.0` (skill overlap ratio)
- **Final Score**: `0.0` to `1.0` (weighted combination: 70% TF-IDF + 30% Skill)

---

## Workflow Example

### Complete Frontend Integration Flow

```javascript
// Step 1: Create Collection
async function createCollection(companyId, zipFile) {
  const formData = new FormData();
  formData.append('company_id', companyId);
  formData.append('zip_file', zipFile);
  
  const response = await fetch('http://localhost:8000/collections/create', {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  const data = await response.json();
  return data.collection_id;
}

// Step 2: Process Collection
async function processCollection(companyId, collectionId) {
  const response = await fetch(
    `http://localhost:8000/collections/${collectionId}/process`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_id: companyId })
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

// Step 3: Rank Collection
async function rankCollection(companyId, collectionId, jdText, topK = null) {
  const body = {
    company_id: companyId,
    jd_text: jdText
  };
  
  if (topK !== null) {
    body.top_k = topK;
  }
  
  const response = await fetch(
    `http://localhost:8000/collections/${collectionId}/rank`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

// Step 4: Get Reports
async function getReports(companyId, collectionId, includeResults = false) {
  const params = new URLSearchParams({
    company_id: companyId,
    include_results: includeResults.toString()
  });
  
  const response = await fetch(
    `http://localhost:8000/collections/${collectionId}/report?${params}`
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

// Complete workflow
async function processResumes(companyId, zipFile, jdText) {
  try {
    // Phase 1: Upload
    const collectionId = await createCollection(companyId, zipFile);
    console.log('Collection created:', collectionId);
    
    // Phase 2: Process
    const processResult = await processCollection(companyId, collectionId);
    console.log('Processing stats:', processResult.details.stats);
    
    // Phase 3: Rank
    const rankResult = await rankCollection(companyId, collectionId, jdText, 10);
    console.log('Ranked resumes:', rankResult.details.ranked_count);
    
    // Phase 4: Get Results
    const reports = await getReports(companyId, collectionId, true);
    console.log('Top candidate:', reports.phase3.ranking_results[0]);
    
    return reports;
  } catch (error) {
    console.error('Error:', error.message);
    throw error;
  }
}
```

---

## Error Handling Best Practices

### Recommended Error Handling Pattern

```javascript
async function apiCall(url, options) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const error = await response.json();
      
      // Handle specific status codes
      switch (response.status) {
        case 400:
          // Bad request - validation error
          throw new ValidationError(error.detail);
        case 404:
          // Not found
          throw new NotFoundError(error.detail);
        case 500:
          // Server error
          throw new ServerError(error.detail);
        default:
          throw new Error(error.detail);
      }
    }
    
    return await response.json();
  } catch (error) {
    // Handle network errors
    if (error instanceof TypeError) {
      throw new NetworkError('Network request failed');
    }
    throw error;
  }
}
```

---

## Rate Limiting

Currently, the API does not implement rate limiting. However, it's recommended to:

- Implement client-side throttling for large batch operations
- Show loading indicators for long-running operations (processing/ranking)
- Consider implementing retry logic with exponential backoff

---

## File Format Requirements

### Supported Resume Formats

- **PDF** (`.pdf`) - Standard PDF documents
- **Word Documents** (`.docx`) - Microsoft Word format
- **Text Files** (`.txt`) - Plain text files

### ZIP File Requirements

- Must be a valid ZIP archive
- Must contain at least one resume file
- File names should be descriptive (e.g., `john_doe_resume.pdf`)
- Avoid special characters in filenames

---

## Notes for Frontend Developers

1. **Collection ID Storage**: Always store the `collection_id` returned from Phase 1. It's required for all subsequent operations.

2. **Async Operations**: Processing and ranking can take time. Consider implementing:
   - Progress indicators
   - Polling mechanisms
   - WebSocket connections (if available)

3. **Error Messages**: The API provides descriptive error messages in the `detail` field. Display these to users for better UX.

4. **Data Validation**: Validate inputs client-side before sending requests:
   - Ensure `company_id` is not empty
   - Ensure `jd_text` is not empty (for ranking)
   - Ensure ZIP file is valid before upload

5. **Response Handling**: Check for `null` values in reports - phases may not be completed yet.

6. **Score Display**: Format scores to 2-4 decimal places for readability (e.g., `0.8234` → `82.34%`).

7. **Pagination**: For large result sets, consider implementing client-side pagination or requesting `top_k` during ranking.

---

## API Versioning

Current API version: **1.0.0**

The API version is available via the root endpoint (`GET /`). Future versions may introduce breaking changes, which will be documented separately.

---

## Support and Contact

For API issues or questions, refer to the project repository or contact the development team.

