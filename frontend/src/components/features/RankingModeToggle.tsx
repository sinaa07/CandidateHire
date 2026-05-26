"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronRight, Loader2, RefreshCw, Sparkles } from "lucide-react"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Button } from "@/components/ui/button"
import {
  getSkillMap,
  getSkillMapStatus,
  rebuildSkillMap,
} from "@/utils/api.v2"
import type { RankingMode, SkillMapStatusValue } from "@/types/v2"

const CONTEXTUAL_ENABLED =
  process.env.NEXT_PUBLIC_CONTEXTUAL_ENABLED !== "false"

type Props = {
  jobId: string
  companyId: string
  currentMode: RankingMode
  skillMapStatus: SkillMapStatusValue
  onModeChange: (mode: RankingMode) => void
  onSkillMapStatusChange?: (status: SkillMapStatusValue) => void
}

export function RankingModeToggle({
  jobId,
  companyId,
  currentMode,
  skillMapStatus,
  onModeChange,
  onSkillMapStatusChange,
}: Props) {
  const [status, setStatus] = useState<SkillMapStatusValue>(skillMapStatus)
  const [activating, setActivating] = useState(false)
  const [mapOpen, setMapOpen] = useState(false)
  const [skillMap, setSkillMap] = useState<Record<string, string[]> | null>(null)
  const [mapLoading, setMapLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pendingSelectRef = useRef(false)

  const updateStatus = useCallback(
    (next: SkillMapStatusValue) => {
      setStatus(next)
      onSkillMapStatusChange?.(next)
    },
    [onSkillMapStatusChange]
  )

  useEffect(() => {
    setStatus(skillMapStatus)
  }, [skillMapStatus])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const pollUntilReady = useCallback(() => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const res = await getSkillMapStatus(companyId, jobId)
        updateStatus(res.status)
        if (res.status === "ready") {
          stopPolling()
          setActivating(false)
          if (pendingSelectRef.current) {
            pendingSelectRef.current = false
            onModeChange("contextual")
          }
        } else if (res.status === "failed") {
          stopPolling()
          setActivating(false)
          pendingSelectRef.current = false
        }
      } catch {
        stopPolling()
        setActivating(false)
      }
    }, 3000)
  }, [companyId, jobId, onModeChange, stopPolling, updateStatus])

  useEffect(() => {
    if (status === "building") {
      pollUntilReady()
    }
    return () => stopPolling()
  }, [status, pollUntilReady, stopPolling])

  const startBuild = async () => {
    setActivating(true)
    updateStatus("building")
    try {
      await rebuildSkillMap(companyId, jobId)
      pollUntilReady()
    } catch {
      updateStatus("failed")
      setActivating(false)
    }
  }

  const selectKeyword = () => {
    if (currentMode !== "keyword") onModeChange("keyword")
  }

  const selectContextual = async () => {
    if (!CONTEXTUAL_ENABLED || currentMode === "contextual") return

    if (status === "ready") {
      onModeChange("contextual")
      return
    }

    if (status === "pending" || status === "failed") {
      pendingSelectRef.current = true
      await startBuild()
      return
    }
  }

  const handleRetry = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await startBuild()
  }

  const loadSkillMap = async () => {
    if (skillMap) return
    setMapLoading(true)
    try {
      const res = await getSkillMap(companyId, jobId)
      setSkillMap(res.skill_implied_by_map)
    } catch {
      setSkillMap(null)
    } finally {
      setMapLoading(false)
    }
  }

  useEffect(() => {
    if (mapOpen && currentMode === "contextual" && status === "ready") {
      loadSkillMap()
    }
  }, [mapOpen, currentMode, status])

  const keywordSelected = currentMode === "keyword"
  const contextualSelected = currentMode === "contextual"
  const contextualDisabled =
    !CONTEXTUAL_ENABLED ||
    status === "building" ||
    activating ||
    (status !== "ready" && status !== "pending" && status !== "failed")

  return (
    <div className="mb-6 space-y-4">
      <h2 className="text-sm font-semibold text-foreground">Ranking mode</h2>
      <div className="grid gap-4 md:grid-cols-2">
        {/* Keyword card */}
        <button
          type="button"
          onClick={selectKeyword}
          className={`rounded-xl border-2 p-5 text-left transition-all ${
            keywordSelected
              ? "border-[#6366F1] bg-[#EEF2FF]"
              : "border-border bg-card hover:border-[#6366F1]/40"
          }`}
        >
          <h3 className="font-semibold text-foreground">Keyword Ranking</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Fast string-based skill matching
          </p>
          <p className="mt-3 text-xs text-muted-foreground">
            Fast · Exact match · No AI cost
          </p>
          {keywordSelected && (
            <span className="mt-3 inline-block rounded-full bg-[#6366F1] px-2 py-0.5 text-xs text-white">
              Selected
            </span>
          )}
        </button>

        {/* Contextual card */}
        <div className="relative">
          {!CONTEXTUAL_ENABLED && (
            <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-background/80 backdrop-blur-sm">
              <span className="rounded-full bg-muted px-3 py-1 text-sm font-medium text-muted-foreground">
                Coming soon
              </span>
            </div>
          )}
          <button
            type="button"
            onClick={selectContextual}
            disabled={contextualDisabled}
            className={`relative w-full rounded-xl border-2 p-5 text-left transition-all ${
              contextualSelected
                ? "border-[#6366F1] bg-[#EEF2FF]"
                : "border-border bg-card hover:border-[#6366F1]/40"
            } ${contextualDisabled ? "cursor-not-allowed opacity-70" : ""}`}
          >
            <span className="absolute right-3 top-3 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
              ★ PRO
            </span>
            <h3 className="pr-16 font-semibold text-foreground">Contextual Ranking</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              AI-powered skill inference
            </p>

            {status === "ready" && (
              <p className="mt-3 text-xs text-[#6366F1]">
                AI-powered · Implies related skills · Recommended
              </p>
            )}
            {(status === "building" || activating) && (
              <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Building skill map...
              </p>
            )}
            {status === "pending" && !activating && (
              <p className="mt-3 text-xs text-muted-foreground">Click to enable</p>
            )}
            {status === "failed" && (
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-destructive">Build failed</span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 px-2 text-xs"
                  onClick={handleRetry}
                >
                  <RefreshCw className="h-3 w-3" />
                  Retry
                </Button>
              </div>
            )}
            {contextualSelected && status === "ready" && (
              <span className="mt-3 inline-block rounded-full bg-[#6366F1] px-2 py-0.5 text-xs text-white">
                Selected
              </span>
            )}
          </button>
        </div>
      </div>

      {contextualSelected && status === "ready" && CONTEXTUAL_ENABLED && (
        <Collapsible open={mapOpen} onOpenChange={setMapOpen}>
          <div className="rounded-xl border border-border bg-card">
            <CollapsibleTrigger className="flex w-full items-center justify-between p-4 text-left text-sm font-semibold">
              <span className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-500" />
                What the AI knows
              </span>
              {mapOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </CollapsibleTrigger>
            <CollapsibleContent className="border-t border-border p-4">
              {mapLoading && (
                <p className="text-sm text-muted-foreground">Loading skill map...</p>
              )}
              {!mapLoading && skillMap && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="pb-2 pr-4 font-medium">JD Skill</th>
                        <th className="pb-2 font-medium">Implied By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(skillMap).map(([skill, implied]) => (
                        <tr key={skill} className="border-b border-border/50">
                          <td className="py-2 pr-4 align-top font-medium">{skill}</td>
                          <td className="py-2 text-muted-foreground">
                            {implied.join(", ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {!mapLoading && !skillMap && (
                <p className="text-sm text-muted-foreground">Could not load skill map.</p>
              )}
            </CollapsibleContent>
          </div>
        </Collapsible>
      )}
    </div>
  )
}
