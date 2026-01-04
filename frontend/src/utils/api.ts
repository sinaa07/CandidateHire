const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function createCollection(companyId: string, zipFile: File) {
  const formData = new FormData()
  formData.append("company_id", companyId)
  formData.append("zip_file", zipFile)

  const response = await fetch(`${API_BASE_URL}/collections/create`, {
    method: "POST",
    body: formData,
  })

  return handleApiResponse(response)
}

export async function processCollection(collectionId: string, companyId: string) {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId }),
  })

  return handleApiResponse(response)
}

export async function rankCollectionText(collectionId: string, companyId: string, jdText: string, topK?: number) {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      company_id: companyId,
      jd_text: jdText,
      ...(topK && { top_k: topK }),
    }),
  })

  return handleApiResponse(response)
}

export async function rankCollectionFile(collectionId: string, companyId: string, jdFile: File, topK?: number) {
  const formData = new FormData()
  formData.append("company_id", companyId)
  formData.append("jd_file", jdFile)
  if (topK) formData.append("top_k", topK.toString())

  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/rank-file`, {
    method: "POST",
    body: formData,
  })

  return handleApiResponse(response)
}

export async function getReport(collectionId: string, companyId: string) {
  const response = await fetch(
    `${API_BASE_URL}/collections/${collectionId}/report?company_id=${companyId}&include_results=true`,
  )

  return handleApiResponse(response)
}

export async function checkOutputs(collectionId: string, companyId: string) {
  const response = await fetch(`${API_BASE_URL}/collections/${collectionId}/outputs?company_id=${companyId}`)

  return handleApiResponse(response)
}
