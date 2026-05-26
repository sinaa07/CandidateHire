"use client"

import { Fragment, useCallback, useEffect, useMemo, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { format } from "date-fns"
import { ChevronDown, ChevronRight, Download } from "lucide-react"
import { V2Nav } from "@/components/v2/V2Nav"
import { StatusBadge } from "@/components/v2/StatusBadge"
import { RankingModeToggle } from "@/components/features/RankingModeToggle"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  exportCSV,
  getJob,
  getRankings,
  getSkillMapStatus,
  rerank,
  saveRankingConfig,
  triggerRank,
  updateJob,
} from "@/utils/api.v2"
import { getCompanyId } from "@/utils/companyId"
import type {
  JobRead,
  LikelyCoveredSkill,
  RankingListItem,
  RankingConfig,
  RankingMode,
  SkillMapStatusValue,
} from "@/types/v2"

const DEFAULT_WEIGHTS = {
  semantic: 0.45,
  skill_match: 0.3,
  experience: 0.15,
  education: 0.1,
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, (value ?? 0) * 100))
  return (
    <div className="mb-2">
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{(value ?? 0).toFixed(2)}</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className="h-2 rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function SkillPills({
  skills,
  className,
}: {
  skills: string[]
  className: string
}) {
  if (!skills.length) {
    return <span className="text-xs text-muted-foreground">None</span>
  }
  return (
    <>
      {skills.map((s) => (
        <span key={s} className={`rounded-full px-2 py-0.5 text-xs ${className}`}>
          {s}
        </span>
      ))}
    </>
  )
}

function LikelyCoveredPills({ items }: { items: LikelyCoveredSkill[] }) {
  if (!items.length) {
    return <span className="text-xs text-muted-foreground">None</span>
  }
  return (
    <>
      {items.map((item) => (
        <span
          key={item.skill}
          title={`covered by: ${item.covered_by.join(", ")}`}
          className="cursor-help rounded-full bg-[#EFF6FF] px-2 py-0.5 text-xs text-[#3B82F6]"
        >
          {item.skill}
        </span>
      ))}
    </>
  )
}

function CandidateSkillsPanel({
  item,
  isContextual,
}: {
  item: RankingListItem
  isContextual: boolean
}) {
  if (!isContextual) {
    return (
      <div>
        <h4 className="mb-2 text-sm font-semibold">Missing skills</h4>
        <div className="flex flex-wrap gap-1">
          <SkillPills
            skills={item.missing_skills}
            className="bg-[#fef2f2] text-[#EF4444]/80"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="mb-2 text-sm font-semibold">Matched skills</h4>
        <div className="flex flex-wrap gap-1">
          <SkillPills skills={item.matched_skills} className="bg-[#ecfdf5] text-[#10B981]" />
        </div>
      </div>
      <div>
        <h4 className="mb-2 text-sm font-semibold">Implied / covered</h4>
        <div className="flex flex-wrap gap-1">
          <LikelyCoveredPills items={item.likely_covered_skills ?? []} />
        </div>
      </div>
      <div>
        <h4 className="mb-2 text-sm font-semibold">Genuinely missing skills</h4>
        <div className="flex flex-wrap gap-1">
          <SkillPills
            skills={item.truly_missing_skills ?? []}
            className="bg-[#fef2f2] text-[#EF4444]/80"
          />
        </div>
      </div>
    </div>
  )
}

export default function RankingsPage() {
  const params = useParams()
  const jobId = params.jobId as string
  const companyId = getCompanyId()

  const [job, setJob] = useState<JobRead | null>(null)
  const [items, setItems] = useState<RankingListItem[]>([])
  const [rankingMode, setRankingMode] = useState<RankingMode>("keyword")
  const [skillMapStatus, setSkillMapStatus] = useState<SkillMapStatusValue>("pending")
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [weightsOpen, setWeightsOpen] = useState(true)
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS)
  const [loading, setLoading] = useState(true)
  const [tableLoading, setTableLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reranking, setReranking] = useState(false)
  const [saving, setSaving] = useState(false)

  const weightSum = useMemo(
    () => weights.semantic + weights.skill_match + weights.experience + weights.education,
    [weights]
  )
  const weightsValid = weightSum >= 0.99 && weightSum <= 1.01

  const load = useCallback(async () => {
    if (!companyId || !jobId) return
    setLoading(true)
    setError(null)
    try {
      const [jobData, rankings, mapStatus] = await Promise.all([
        getJob(companyId, jobId),
        getRankings(companyId, jobId, { limit: 50 }),
        getSkillMapStatus(companyId, jobId).catch(() => null),
      ])
      setJob(jobData)
      setItems(rankings.items)
      setRankingMode((jobData.ranking_mode as RankingMode) || "keyword")
      setSkillMapStatus(
        (mapStatus?.status as SkillMapStatusValue) ||
          (jobData.skill_map_status as SkillMapStatusValue) ||
          "pending"
      )
      if (jobData.ranking_config?.weights) {
        setWeights({ ...DEFAULT_WEIGHTS, ...jobData.ranking_config.weights })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rankings")
    } finally {
      setLoading(false)
    }
  }, [companyId, jobId])

  useEffect(() => {
    load()
  }, [load])

  const sortedItems = useMemo(() => {
    const passed = items.filter((i) => i.passed_hard_filter)
    const failed = items.filter((i) => !i.passed_hard_filter)
    passed.sort((a, b) => (a.rank_position ?? 0) - (b.rank_position ?? 0))
    failed.sort((a, b) => (b.final_score ?? 0) - (a.final_score ?? 0))
    return [...passed, ...failed]
  }, [items])

  const rankedAt = items[0]?.ranked_at
  const isContextualMode = rankingMode === "contextual"

  const contextualSummary = useMemo(() => {
    if (!isContextualMode) return null
    let inferredCount = 0
    let candidateCount = 0
    for (const item of items) {
      const covered = item.likely_covered_skills ?? []
      if (covered.length > 0) {
        candidateCount += 1
        inferredCount += covered.length
      }
    }
    return { inferredCount, candidateCount }
  }, [items, isContextualMode])

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const refreshRankings = useCallback(
    async (mode: RankingMode) => {
      if (!companyId) return
      const rankings = await getRankings(companyId, jobId, {
        limit: 50,
        mode_filter: mode,
      })
      setItems(rankings.items)
    },
    [companyId, jobId]
  )

  const handleModeChange = async (mode: RankingMode) => {
    if (!companyId || mode === rankingMode) return
    setTableLoading(true)
    setError(null)
    try {
      await updateJob(companyId, jobId, { ranking_mode: mode })
      await triggerRank(companyId, jobId, undefined, mode)
      await refreshRankings(mode)
      setRankingMode(mode)
      setJob((j) => (j ? { ...j, ranking_mode: mode } : j))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to switch ranking mode")
    } finally {
      setTableLoading(false)
    }
  }

  const handleRerank = async () => {
    if (!companyId || !weightsValid) return
    setReranking(true)
    try {
      const results = await rerank(companyId, jobId, weights)
      const byId = new Map(results.map((r) => [r.candidate_id, r]))
      setItems((prev) =>
        prev.map((item) => {
          const r = byId.get(item.candidate_id)
          if (!r) return item
          return {
            ...item,
            final_score: r.final_score,
            rank_position: r.rank_position,
            score_breakdown: r.score_breakdown,
            matched_skills: r.matched_skills,
            missing_skills: r.missing_skills,
            truly_missing_skills: r.truly_missing_skills,
            likely_covered_skills: r.likely_covered_skills,
            ranking_mode_used: r.ranking_mode_used,
          }
        })
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rerank failed")
    } finally {
      setReranking(false)
    }
  }

  const handleSaveConfig = async () => {
    if (!companyId || !job || !weightsValid) return
    setSaving(true)
    try {
      const config: RankingConfig = {
        weights,
        hard_filters: job.ranking_config?.hard_filters ?? {
          min_skill_overlap: 0,
          min_experience_years: 0,
        },
      }
      await saveRankingConfig(companyId, jobId, config)
      setJob((j) => (j ? { ...j, ranking_config: config } : j))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  const handleExport = async () => {
    if (!companyId) return
    try {
      const blob = await exportCSV(companyId, jobId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `rankings_${jobId}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed")
    }
  }

  const updateWeight = (key: keyof typeof weights, value: number) => {
    setWeights((w) => ({ ...w, [key]: value }))
  }

  return (
    <div className="min-h-screen bg-background">
      <V2Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link href={`/jobs/${jobId}`} className="text-sm text-primary hover:underline">
              ← Back to Job
            </Link>
            <h1 className="mt-2 text-2xl font-bold text-foreground">
              {job?.title ?? "Rankings"}
            </h1>
            <p className="text-sm text-muted-foreground">
              Ranked {items.length} candidate{items.length !== 1 ? "s" : ""}
              {rankedAt && ` · ${format(new Date(rankedAt), "MMM d, yyyy HH:mm")}`}
            </p>
          </div>
          <Button variant="outline" onClick={handleExport} className="gap-2">
            <Download size={16} />
            Export CSV
          </Button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {companyId && (
          <RankingModeToggle
            jobId={jobId}
            companyId={companyId}
            currentMode={rankingMode}
            skillMapStatus={skillMapStatus}
            onModeChange={handleModeChange}
            onSkillMapStatusChange={setSkillMapStatus}
          />
        )}

        <Collapsible open={weightsOpen} onOpenChange={setWeightsOpen} className="mb-6">
          <div className="rounded-xl border border-border bg-card shadow-sm">
            <CollapsibleTrigger className="flex w-full items-center justify-between p-4 text-left font-semibold">
              Ranking weights
              {weightsOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </CollapsibleTrigger>
            <CollapsibleContent className="border-t border-border p-4">
              <div className="grid gap-6 md:grid-cols-2">
                {(
                  [
                    ["semantic", "Semantic similarity", 0.45],
                    ["skill_match", "Skill match", 0.3],
                    ["experience", "Experience", 0.15],
                    ["education", "Education", 0.1],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key}>
                    <div className="mb-2 flex justify-between text-sm">
                      <span>{label}</span>
                      <span className="font-mono">{weights[key].toFixed(2)}</span>
                    </div>
                    <Slider
                      value={[weights[key]]}
                      min={0}
                      max={1}
                      step={0.01}
                      onValueChange={([v]) => updateWeight(key, v)}
                    />
                  </div>
                ))}
              </div>
              <p
                className={`mt-4 text-sm ${weightsValid ? "text-[#10B981]" : "text-[#F59E0B]"}`}
              >
                Sum: {weightSum.toFixed(2)}
                {!weightsValid && " — weights should sum to 1.0"}
              </p>
              <div className="mt-4 flex gap-2">
                <Button onClick={handleRerank} disabled={!weightsValid || reranking}>
                  {reranking ? "Reranking..." : "Rerank"}
                </Button>
                <Button variant="outline" onClick={handleSaveConfig} disabled={!weightsValid || saving}>
                  {saving ? "Saving..." : "Save as default"}
                </Button>
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>

        {isContextualMode && contextualSummary && items.length > 0 && (
          <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Contextual mode: {contextualSummary.inferredCount} skill
            {contextualSummary.inferredCount !== 1 ? "s" : ""} inferred across{" "}
            {contextualSummary.candidateCount} candidate
            {contextualSummary.candidateCount !== 1 ? "s" : ""}
          </p>
        )}

        {(loading || tableLoading) && (
          <p className="mb-4 text-muted-foreground">
            {tableLoading ? "Updating rankings..." : "Loading rankings..."}
          </p>
        )}

        <div
          className={`overflow-hidden rounded-xl border border-border bg-card shadow-sm ${
            tableLoading ? "pointer-events-none opacity-60" : ""
          }`}
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10" />
                <TableHead>Rank</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Final</TableHead>
                <TableHead>Semantic</TableHead>
                <TableHead>Skill</TableHead>
                <TableHead>Exp</TableHead>
                <TableHead>Edu</TableHead>
                <TableHead>Filter</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedItems.map((item) => {
                const isExpanded = expanded.has(item.candidate_id)
                const failed = !item.passed_hard_filter
                const rowContextual =
                  (item.ranking_mode_used as RankingMode) === "contextual" || isContextualMode
                return (
                  <Fragment key={item.candidate_id}>
                    <TableRow
                      className={failed ? "bg-muted/40 text-muted-foreground" : undefined}
                    >
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => toggleExpand(item.candidate_id)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        </button>
                      </TableCell>
                      <TableCell className="font-mono">{item.rank_position ?? "—"}</TableCell>
                      <TableCell className="max-w-[200px] truncate font-medium">
                        {item.filename}
                      </TableCell>
                      <TableCell className="font-semibold">{item.final_score?.toFixed(3)}</TableCell>
                      <TableCell>{item.score_breakdown.semantic?.toFixed(2) ?? "—"}</TableCell>
                      <TableCell>{item.score_breakdown.skill_match?.toFixed(2) ?? "—"}</TableCell>
                      <TableCell>{item.score_breakdown.experience?.toFixed(2) ?? "—"}</TableCell>
                      <TableCell>{item.score_breakdown.education?.toFixed(2) ?? "—"}</TableCell>
                      <TableCell>
                        {failed ? (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                            Did not meet filters
                          </span>
                        ) : (
                          <StatusBadge status="passed" />
                        )}
                      </TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow key={`${item.candidate_id}-detail`} className="bg-muted/20">
                        <TableCell colSpan={9} className="p-4">
                          <div className="grid gap-6 md:grid-cols-2">
                            <div>
                              <h4 className="mb-3 text-sm font-semibold">Score breakdown</h4>
                              <ScoreBar label="Semantic" value={item.score_breakdown.semantic ?? 0} />
                              <ScoreBar label="Skill match" value={item.score_breakdown.skill_match ?? 0} />
                              <ScoreBar label="Experience" value={item.score_breakdown.experience ?? 0} />
                              <ScoreBar label="Education" value={item.score_breakdown.education ?? 0} />
                            </div>
                            <CandidateSkillsPanel item={item} isContextual={rowContextual} />
                          </div>
                          {item.top_matching_chunks?.length > 0 && (
                            <div className="mt-4">
                              <h4 className="mb-2 text-sm font-semibold">Top matching chunks</h4>
                              <ul className="space-y-2">
                                {item.top_matching_chunks.map((chunk, i) => (
                                  <li
                                    key={i}
                                    className="rounded-lg border border-border bg-card p-3 text-xs"
                                  >
                                    <span className="font-mono text-primary">
                                      {(chunk.cosine_score ?? 0).toFixed(3)}
                                    </span>
                                    <p className="mt-1 text-muted-foreground">{chunk.chunk_text}</p>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                )
              })}
            </TableBody>
          </Table>
        </div>

        {!loading && !tableLoading && items.length === 0 && (
          <p className="mt-6 text-center text-muted-foreground">
            No rankings yet. Run indexing and ranking from the job page.
          </p>
        )}
      </main>
    </div>
  )
}
