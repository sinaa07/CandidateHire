// Application types and interfaces

export type Phase = 1 | 2 | 3 | 4

export interface Collection {
  id: string
  company_id: string
  created_at: string
  status: "uploaded" | "processed" | "ranked"
  last_accessed: string
}

export interface ProcessingStats {
  total_files: number
  ok: number
  failed: number
  empty: number
  duplicate: number
}

export interface RankedCandidate {
  rank: number
  filename: string
  tfidf_score: number
  skill_score: number
  final_score: number
  explainability: {
    matched_skills: string[]
    missing_skills: string[]
  }
}

export interface RankingSummary {
  resume_count: number
  ranked_count: number
}

export interface AppState {
  currentCollection: {
    collection_id: string | null
    company_id: string | null
    phase: Phase
    status: {
      uploaded: boolean
      processed: boolean
      ranked: boolean
    }
  }
  processingResults: ProcessingStats | null
  rankingResults: {
    summary: RankingSummary | null
    candidates: RankedCandidate[]
  }
  filters: {
    searchText: string
    minScore: number
    maxScore: number
  }
  compareMode: boolean
  selectedForComparison: string[]
  loading: boolean
  error: string | null
}

export interface ApiResponse<T> {
  status?: string
  collection_id?: string
  details?: T
  [key: string]: any
}
