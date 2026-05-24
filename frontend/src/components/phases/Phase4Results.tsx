"use client"

import { useState, useEffect, useMemo } from "react"
import { RotateCcw, AlertCircle, Loader } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { getReport } from "@/utils/api"
import { formatScore } from "@/utils/formatters"
import { ResultsTable } from "@/components/features/ResultsTable"
import { FiltersBar } from "@/components/features/FiltersBar"
import { CompareSelectionBar } from "@/components/features/CompareSelectionBar"
import { ReRankModal } from "@/components/modals/ReRankModal"
import { ComparisonModal } from "@/components/modals/ComparisonModal"
import { NERTestingSection } from "@/components/features/NERTestingSection"

export function Phase4Results() {
  const {
    currentCollection,
    rankingResults,
    setRankingResults,
    compareMode,
    setCompareMode,
    selectedForComparison,
    setError,
    error,
  } = useAppContext()

  const { collection_id, company_id } = currentCollection
  const [showReRankModal, setShowReRankModal] = useState(false)
  const [showComparisonModal, setShowComparisonModal] = useState(false)
  const [isLoadingReport, setIsLoadingReport] = useState(true)
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null)

  useEffect(() => {
    if (!collection_id || !company_id) return

    const fetchReport = async () => {
      setIsLoadingReport(true)
      try {
        const report = await getReport(collection_id, company_id)
        const candidates = report.phase3?.ranking_results || []
        setRankingResults({
          summary: report.phase3?.ranking_summary || { resume_count: 0, ranked_count: 0 },
          candidates,
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load results")
      } finally {
        setIsLoadingReport(false)
      }
    }

    if (!rankingResults.candidates.length) {
      fetchReport()
    } else {
      setIsLoadingReport(false)
    }
  }, [collection_id, company_id])

  const candidates = rankingResults.candidates || []
  const summary = rankingResults.summary || { resume_count: 0, ranked_count: 0 }

  const avgScore = useMemo(() => {
    if (candidates.length === 0) return 0
    return candidates.reduce((acc, c) => acc + c.final_score, 0) / candidates.length
  }, [candidates])

  const topScore = candidates.length > 0 ? candidates[0].final_score : 0

  if (isLoadingReport) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader size={40} className="text-primary animate-spin" />
      </div>
    )
  }

  return (
    <div className="px-6 py-8 space-y-6">
      <header className="flex flex-wrap justify-between items-end gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Results & Analysis</h2>
          <p className="text-muted-foreground mt-1 max-w-xl">
            Review ranked candidates, filter by score, and compare top picks.
          </p>
        </div>
        <button
          onClick={() => setShowReRankModal(true)}
          className="btn-secondary flex items-center gap-2"
        >
          <RotateCcw size={16} />
          Re-rank
        </button>
      </header>

      {/* Summary cards — 4 columns on desktop */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="dashboard-card p-5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Total</p>
          <p className="text-3xl font-bold text-foreground mt-1">{summary.resume_count}</p>
          <p className="text-xs text-muted-foreground mt-1">Total Resumes</p>
        </div>
        <div className="dashboard-card p-5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Ranked</p>
          <p className="text-3xl font-bold text-foreground mt-1">{summary.ranked_count}</p>
          <p className="text-xs text-muted-foreground mt-1">Candidates Ranked</p>
        </div>
        <div className="dashboard-card p-5">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Avg Score</p>
          <p className="text-3xl font-bold text-foreground mt-1">{formatScore(avgScore)}</p>
          <p className="text-xs text-muted-foreground mt-1">Pipeline Average</p>
        </div>
        <div className="rounded-xl p-5 gradient-primary text-white shadow-card">
          <p className="text-xs font-medium text-white/80 uppercase tracking-wide">Top Score</p>
          <p className="text-3xl font-bold mt-1">{formatScore(topScore)}</p>
          <p className="text-xs text-white/70 mt-1">Best Match</p>
        </div>
      </div>

      {/* Action bar */}
      <div className="dashboard-card px-4 py-3 flex items-center justify-between gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
            className="w-4 h-4 rounded border-border accent-primary"
          />
          <span className="text-sm font-medium text-foreground">Compare Mode</span>
        </label>
        <span className="text-xs text-muted-foreground hidden md:inline">
          Select up to 3 candidates to compare side-by-side
        </span>
      </div>

      <FiltersBar />

      {selectedFilename && collection_id && company_id && (
        <NERTestingSection
          collectionId={collection_id}
          companyId={company_id}
          selectedFilename={selectedFilename}
        />
      )}

      {error && (
        <div className="bg-error-50 border border-error-100 rounded-lg p-4 flex gap-3">
          <AlertCircle size={20} className="text-error shrink-0" />
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      <ResultsTable candidates={candidates} onRowClick={setSelectedFilename} />

      {compareMode && selectedForComparison.length > 0 && (
        <CompareSelectionBar
          selectedCount={selectedForComparison.length}
          onCompare={() => setShowComparisonModal(true)}
        />
      )}

      {showReRankModal && <ReRankModal onClose={() => setShowReRankModal(false)} />}
      {showComparisonModal && (
        <ComparisonModal
          candidates={candidates.filter((c) => selectedForComparison.includes(c.filename))}
          onClose={() => setShowComparisonModal(false)}
        />
      )}
    </div>
  )
}
