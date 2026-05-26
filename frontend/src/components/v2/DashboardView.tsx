"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { Loader2 } from "lucide-react"
import { V2Nav } from "@/components/v2/V2Nav"
import { StatCard } from "@/components/v2/StatCard"
import { StatusBadge } from "@/components/v2/StatusBadge"
import { CreateJobModal } from "@/components/v2/CreateJobModal"
import { Button } from "@/components/ui/button"
import { CompanyCredentialsSetup } from "@/components/v2/CompanyCredentialsSetup"
import { getDashboard } from "@/utils/api.v2"
import { getApiKey, getCompanyId } from "@/utils/companyId"
import type { DashboardResponse, JobSummary } from "@/types/v2"

function RankingModeBadge({ job }: { job: JobSummary }) {
  const mode = job.ranking_mode || "keyword"
  const mapStatus = job.skill_map_status

  if (mapStatus === "building") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
        <Loader2 className="h-3 w-3 animate-spin" />
        ★ Building...
      </span>
    )
  }

  if (mode === "contextual") {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
        ★ Contextual
      </span>
    )
  }

  return (
    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
      Keyword
    </span>
  )
}

export function DashboardView() {
  const [companyId, setCompanyId] = useState("")
  const [needsSetup, setNeedsSetup] = useState(false)
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const load = useCallback(async () => {
    const id = getCompanyId()
    const key = getApiKey()
    setCompanyId(id)
    if (!id || !key) {
      setNeedsSetup(true)
      setLoading(false)
      return
    }
    setNeedsSetup(false)
    setLoading(true)
    setError(null)
    try {
      const dashboard = await getDashboard(id)
      setData(dashboard)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="min-h-screen bg-background">
      <V2Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Company Dashboard</h1>
            {data?.company && (
              <p className="mt-1 text-sm text-muted-foreground">{data.company.name}</p>
            )}
          </div>
          <Button onClick={() => setModalOpen(true)} className="gradient-primary text-white">
            + New Job
          </Button>
        </div>

        {needsSetup && (
          <CompanyCredentialsSetup
            onSaved={() => {
              setNeedsSetup(false)
              setLoading(true)
              load()
            }}
          />
        )}

        {!needsSetup && loading && <p className="text-muted-foreground">Loading dashboard...</p>}
        {!needsSetup && error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {!needsSetup && data && (
          <>
            <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Total Jobs" value={data.summary.total_jobs} borderColor="#6366F1" />
              <StatCard label="Open Jobs" value={data.summary.open_jobs} borderColor="#10B981" />
              <StatCard label="Total Candidates" value={data.summary.total_candidates} borderColor="#3B82F6" />
              <StatCard label="Ranked Candidates" value={data.summary.ranked_candidates} borderColor="#8B5CF6" />
            </div>

            <h2 className="mb-4 text-lg font-semibold text-foreground">Jobs</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {data.jobs.map((job) => (
                <div
                  key={job.id}
                  className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h3 className="text-base font-bold text-foreground">{job.title}</h3>
                      {job.department && (
                        <p className="text-xs text-muted-foreground">{job.department}</p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <RankingModeBadge job={job} />
                      <StatusBadge status={job.status} />
                      <StatusBadge status={job.pipeline_stage} />
                    </div>
                  </div>

                  <div className="mb-4 grid grid-cols-3 gap-2 text-center text-sm">
                    <div className="rounded-lg bg-muted/50 p-2">
                      <p className="font-semibold text-foreground">{job.resume_count}</p>
                      <p className="text-xs text-muted-foreground">Resumes</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-2">
                      <p className="font-semibold text-foreground">{job.indexed_count}</p>
                      <p className="text-xs text-muted-foreground">Indexed</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-2">
                      <p className="font-semibold text-foreground">
                        {job.top_score != null ? job.top_score.toFixed(2) : "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">Top Score</p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Link href={`/jobs/${job.id}/rankings`} className="flex-1">
                      <Button variant="outline" className="w-full" size="sm">
                        View Rankings
                      </Button>
                    </Link>
                    <Link href={`/jobs/${job.id}`} className="flex-1">
                      <Button className="w-full gradient-primary text-white" size="sm">
                        Manage
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            {data.jobs.length === 0 && (
              <p className="text-center text-muted-foreground">No jobs yet. Create your first job.</p>
            )}
          </>
        )}
      </main>

      {companyId && (
        <CreateJobModal
          open={modalOpen}
          onOpenChange={setModalOpen}
          companyId={companyId}
          onSuccess={load}
        />
      )}
    </div>
  )
}
