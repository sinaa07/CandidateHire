import { handleApiResponse } from "@/utils/api"
import { getApiKey } from "@/utils/companyId"
import type {
  CompanyRead,
  DashboardResponse,
  JobRead,
  JobSummary,
  PipelineStatus,
  RankingsResponse,
  RankingConfig,
  RankingMode,
  RerankResult,
  ResumeListItem,
  RankSummary,
  SkillMapResponse,
  SkillMapStatusResponse,
  UploadResumesResponse,
} from "@/types/v2"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

function v2(path: string): string {
  return `${API_BASE_URL}${path}`
}

function authHeaders(): HeadersInit {
  const apiKey = getApiKey()
  if (!apiKey) return {}
  return { "X-Company-API-Key": apiKey }
}

function mergeHeaders(extra?: HeadersInit): HeadersInit {
  return { ...authHeaders(), ...(extra || {}) }
}

export async function getCompany(companyId: string): Promise<CompanyRead> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}`), { headers: authHeaders() })
  return handleApiResponse<CompanyRead>(res)
}

export async function getDashboard(companyId: string): Promise<DashboardResponse> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/dashboard`), {
    headers: authHeaders(),
  })
  return handleApiResponse<DashboardResponse>(res)
}

export async function createJob(
  companyId: string,
  data: {
    title: string
    department?: string
    status?: string
    jd_text?: string
    jd_file?: File | null
  }
): Promise<JobRead> {
  const form = new FormData()
  form.append("title", data.title)
  if (data.department) form.append("department", data.department)
  form.append("status", data.status || "open")
  if (data.jd_text) form.append("jd_text", data.jd_text)
  if (data.jd_file) form.append("jd_file", data.jd_file)

  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/`), {
    method: "POST",
    headers: authHeaders(),
    body: form,
  })
  return handleApiResponse<JobRead>(res)
}

export async function getJobs(companyId: string): Promise<JobSummary[]> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/`), {
    headers: authHeaders(),
  })
  return handleApiResponse<JobSummary[]>(res)
}

export async function getJob(companyId: string, jobId: string): Promise<JobRead> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}`), {
    headers: authHeaders(),
  })
  return handleApiResponse<JobRead>(res)
}

export async function updateJob(
  companyId: string,
  jobId: string,
  data: Partial<{
    title: string
    department: string
    status: string
    jd_text: string
    ranking_config: RankingConfig
    ranking_mode: RankingMode
  }>
): Promise<JobRead> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}`), {
    method: "PATCH",
    headers: mergeHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(data),
  })
  return handleApiResponse<JobRead>(res)
}

export async function uploadResumes(
  companyId: string,
  jobId: string,
  files: File[],
  zipFile?: File | null
): Promise<UploadResumesResponse> {
  const form = new FormData()
  files.forEach((file) => form.append("files", file))
  if (zipFile) form.append("zip_file", zipFile)

  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/resumes/`), {
    method: "POST",
    headers: authHeaders(),
    body: form,
  })
  return handleApiResponse<UploadResumesResponse>(res)
}

export async function getResumes(companyId: string, jobId: string): Promise<ResumeListItem[]> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/resumes/`), {
    headers: authHeaders(),
  })
  return handleApiResponse<ResumeListItem[]>(res)
}

export async function triggerIndex(companyId: string, jobId: string): Promise<{ message: string; queued: number }> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/index`), {
    method: "POST",
    headers: authHeaders(),
  })
  return handleApiResponse(res)
}

export async function getPipelineStatus(companyId: string, jobId: string): Promise<PipelineStatus> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/status`), {
    headers: authHeaders(),
  })
  return handleApiResponse<PipelineStatus>(res)
}

export async function getSkillMapStatus(
  companyId: string,
  jobId: string
): Promise<SkillMapStatusResponse> {
  const res = await fetch(
    v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/skill-map/status`),
    { headers: authHeaders() }
  )
  return handleApiResponse<SkillMapStatusResponse>(res)
}

export async function getSkillMap(
  companyId: string,
  jobId: string
): Promise<SkillMapResponse> {
  const res = await fetch(
    v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/skill-map`),
    { headers: authHeaders() }
  )
  return handleApiResponse<SkillMapResponse>(res)
}

export async function rebuildSkillMap(
  companyId: string,
  jobId: string
): Promise<{ message: string; job_id: string }> {
  const res = await fetch(
    v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/skill-map/rebuild`),
    { method: "POST", headers: authHeaders() }
  )
  return handleApiResponse(res)
}

export async function triggerRank(
  companyId: string,
  jobId: string,
  configOverride?: Partial<RankingConfig>,
  rankingMode?: RankingMode
): Promise<RankSummary> {
  const body: Record<string, unknown> = {}
  if (configOverride) body.config_override = configOverride
  if (rankingMode) body.ranking_mode = rankingMode

  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/rank`), {
    method: "POST",
    headers: mergeHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  })
  return handleApiResponse<RankSummary>(res)
}

export async function getRankings(
  companyId: string,
  jobId: string,
  params?: {
    limit?: number
    offset?: number
    min_score?: number
    passed_only?: boolean
    mode_filter?: RankingMode
  }
): Promise<RankingsResponse> {
  const search = new URLSearchParams()
  if (params?.limit != null) search.set("limit", String(params.limit))
  if (params?.offset != null) search.set("offset", String(params.offset))
  if (params?.min_score != null) search.set("min_score", String(params.min_score))
  if (params?.passed_only) search.set("passed_only", "true")
  if (params?.mode_filter) search.set("mode_filter", params.mode_filter)
  const qs = search.toString()
  const res = await fetch(
    v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/rankings${qs ? `?${qs}` : ""}`),
    { headers: authHeaders() }
  )
  return handleApiResponse<RankingsResponse>(res)
}

export async function rerank(
  companyId: string,
  jobId: string,
  weights: RankingConfig["weights"]
): Promise<RerankResult[]> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/rerank`), {
    method: "POST",
    headers: mergeHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ weights }),
  })
  return handleApiResponse<RerankResult[]>(res)
}

export async function saveRankingConfig(
  companyId: string,
  jobId: string,
  rankingConfig: RankingConfig
): Promise<JobRead> {
  return updateJob(companyId, jobId, { ranking_config: rankingConfig })
}

export async function exportCSV(companyId: string, jobId: string): Promise<Blob> {
  const res = await fetch(v2(`/api/v2/companies/${companyId}/jobs/${jobId}/pipeline/rankings/export`), {
    headers: authHeaders(),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Export failed (${res.status})`)
  }
  return res.blob()
}
