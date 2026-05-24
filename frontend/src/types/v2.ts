export interface CompanyRead {
  id: string
  name: string
  slug: string
  api_key: string
  created_at: string
  settings: Record<string, unknown>
}

export interface JobSummary {
  id: string
  title: string
  status: string
  department: string | null
  created_at: string
  updated_at: string
  resume_count: number
  indexed_count: number
  top_score: number | null
  pipeline_stage: string
  last_ranked_at: string | null
}

export interface JobRead extends JobSummary {
  company_id: string
  jd_text: string | null
  jd_file_path: string | null
  ranking_config: RankingConfig
}

export interface RankingConfig {
  weights: {
    semantic: number
    skill_match: number
    experience: number
    education: number
  }
  hard_filters: {
    min_skill_overlap: number
    min_experience_years: number
  }
}

export interface DashboardResponse {
  company: {
    id: string
    name: string
    settings: Record<string, unknown>
  }
  summary: {
    total_jobs: number
    open_jobs: number
    total_candidates: number
    indexed_candidates: number
    ranked_candidates: number
  }
  jobs: JobSummary[]
}

export interface ResumeListItem {
  id: string
  filename: string
  status: string
  created_at: string
  indexed: boolean
  ranked: boolean
  index_summary: {
    skills: string[]
    experience_years: number
    education_tier: number
  } | null
}

export interface UploadResumesResponse {
  uploaded: number
  skipped: number
  candidates: { id: string; filename: string; status: string }[]
  job_id: string
}

export interface PipelineStatus {
  total: number
  uploaded: number
  processing: number
  processed: number
  failed: number
  duplicate: number
  indexing_complete: boolean
}

export interface RankSummary {
  job_id: string
  ranked_count: number
  ranked_at: string
  top_candidate: Record<string, unknown> | null
  config_used: RankingConfig
}

export interface MatchingChunk {
  chunk_text: string
  cosine_score: number
  chunk_idx?: number
  section?: string
}

export interface RankingListItem {
  candidate_id: string
  filename: string
  rank_position: number
  final_score: number
  score_breakdown: {
    semantic: number | null
    skill_match: number | null
    experience: number | null
    education: number | null
  }
  matched_skills: string[]
  missing_skills: string[]
  top_matching_chunks: MatchingChunk[]
  passed_hard_filter: boolean
  ranked_at: string
}

export interface RankingsResponse {
  items: RankingListItem[]
  total: number
  limit: number
  offset: number
}

export interface RerankResult {
  candidate_id: string
  final_score: number
  score_breakdown: {
    semantic: number | null
    skill_match: number | null
    experience: number | null
    education: number | null
  }
  matched_skills: string[]
  missing_skills: string[]
  rank_position: number
}
