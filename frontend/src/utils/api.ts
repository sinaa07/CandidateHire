import type { ProcessingStats, RankingSummary, RankedCandidate } from "@/types"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

export async function handleApiResponse<T>(response: Response): Promise<T> {
  // Clone response for error handling (response body can only be read once)
  const clonedResponse = response.clone()
  
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const error = await clonedResponse.json()
      errorMessage = error.detail || error.message || errorMessage
    } catch {
      // If JSON parsing fails, try to get text from original response
      try {
        const text = await response.text()
        errorMessage = text || errorMessage
      } catch {
        // If text parsing also fails, use default message
      }
    }
    throw new Error(errorMessage)
  }
  
  // Handle successful response
  try {
    const text = await response.text()
    if (!text.trim()) {
      throw new Error("Empty response from server")
    }
    return JSON.parse(text) as T
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error(`Invalid JSON response from server: ${error.message}`)
    }
    if (error instanceof Error) {
      throw new Error(`Failed to parse response: ${error.message}`)
    }
    throw new Error("Failed to parse response from server")
  }
}

export interface CreateCollectionResponse {
  status: string
  collection_id: string
  company_id: string
}

export interface CollectionReport {
  collection_id: string
  company_id: string
  meta: any | null
  phase2: {
    validation_report: (ProcessingStats & { files?: any[] }) | null
    duplicate_report: any | null
  }
  phase3: {
    ranking_summary: RankingSummary | null
    ranking_results?: RankedCandidate[]
  }
}

export interface RankingResponse {
  status: string
  collection_id: string
  details: {
    status: string
    resume_count: number
    ranked_count: number
    top_k: number | null
    outputs_generated: string[]
    jd_saved_as?: string
  } | null
}

export async function createCollection(
  companyId: string,
  zipFile: File
): Promise<CreateCollectionResponse> {
  const formData = new FormData()
  formData.append("company_id", companyId)
  formData.append("zip_file", zipFile)

  try {
    const response = await fetch(`${API_BASE_URL}/collections/create`, {
      method: "POST",
      body: formData,
    })

    return await handleApiResponse<CreateCollectionResponse>(response)
  } catch (error) {
    // Handle network errors (CORS, connection refused, etc.)
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error(`Network error: Unable to connect to API at ${API_BASE_URL}. Please check if the backend server is running.`)
    }
    // Re-throw other errors (they're already formatted by handleApiResponse)
    throw error
  }
}


export async function processCollection(collectionId: string, companyId: string) {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId }),
  })

  return handleApiResponse(response)
}

export async function rankCollectionText(
  collectionId: string,
  companyId: string,
  jdText: string,
  topK?: number,
): Promise<RankingResponse> {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      company_id: companyId,
      jd_text: jdText,
      ...(topK && { top_k: topK }),
    }),
  })

  return handleApiResponse<RankingResponse>(response)
}

export async function rankCollectionFile(
  collectionId: string,
  companyId: string,
  jdFile: File,
  topK?: number,
): Promise<RankingResponse> {
  const formData = new FormData()
  formData.append("company_id", companyId)
  formData.append("jd_file", jdFile)
  if (topK) formData.append("top_k", topK.toString())

  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rank-file`, {
    method: "POST",
    body: formData,
  })

  return handleApiResponse<RankingResponse>(response)
}

export async function getReport(collectionId: string, companyId: string): Promise<CollectionReport> {
  const response = await fetch(
    `${API_BASE_URL}/collections/${collectionId}/report?company_id=${companyId}&include_results=true`,
  )

  return handleApiResponse<CollectionReport>(response)
}

export interface EntitiesResponse {
  filename: string
  entities: {
    skills: Record<string, { count: number; contexts: string[]; confidence: number }>
    roles: string[]
    organizations: string[]
    education: { degree: string | null; field: string | null }
    experience: {
      years_min: number | null
      years_max: number | null
      earliest_date: string | null
      latest_date: string | null
    }
    locations: string[]
  }
}

export async function getResumeEntities(
  collectionId: string,
  filename: string,
  companyId: string
): Promise<EntitiesResponse> {
  const response = await fetch(
    `${API_BASE_URL}/collections/${collectionId}/entities/${encodeURIComponent(filename)}?company_id=${companyId}`
  )
  return handleApiResponse<EntitiesResponse>(response)
}

export async function checkOutputs(collectionId: string, companyId: string) {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/outputs?company_id=${companyId}`)

  return handleApiResponse(response)
}

export interface RAGStatusResponse {
  rag_available: boolean
  features_enabled: {
    phase2_complete: boolean
    phase3_available: boolean
    llm_providers: string[]
  }
  index_built: boolean
  index_stats: any | null
}

export interface RAGQueryRequest {
  company_id: string
  query: string
  top_k?: number
  filters?: {
    use_ranking?: boolean
    min_rank_position?: number
    max_rank_position?: number
    min_ranking_score?: number
    required_skills?: string[]
  }
  include_context?: boolean
}

export interface RAGQueryResponse {
  task_id: string
  status: string
}

export async function getRAGStatus(collectionId: string, companyId: string): Promise<RAGStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rag/status?company_id=${companyId}`)
  return handleApiResponse<RAGStatusResponse>(response)
}

export async function initializeRAG(collectionId: string, companyId: string) {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rag/initialize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId }),
  })
  return handleApiResponse(response)
}

export async function queryRAG(collectionId: string, request: RAGQueryRequest): Promise<RAGQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rag/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  return handleApiResponse<RAGQueryResponse>(response)
}
