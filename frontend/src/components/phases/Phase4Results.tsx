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
    setLoading,
    setError,
    error,
    loading,
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
    const sum = candidates.reduce((acc, c) => acc + c.final_score, 0)
    return sum / candidates.length
  }, [candidates])

  const topScore = candidates.length > 0 ? candidates[0].final_score : 0

  if (isLoadingReport) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader size={40} className="text-blue-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="px-6 py-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h2 className="text-4xl font-bold text-[#262626] mb-2">Ranking Results</h2>
        <p className="text-[#737373]">Review and compare top candidates</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-[#E5E5E5] rounded-lg p-6 text-center shadow-card">
          <div className="text-3xl font-bold text-[#262626] mb-1">{summary.resume_count}</div>
          <div className="text-sm text-[#737373]">Total</div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-lg p-6 text-center shadow-card">
          <div className="text-3xl font-bold text-[#262626] mb-1">{candidates.length}</div>
          <div className="text-sm text-[#737373]">Ranked</div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-lg p-6 text-center shadow-card">
          <div className="text-3xl font-bold text-[#262626] mb-1">{formatScore(avgScore).replace("%", "")}</div>
          <div className="text-sm text-[#737373]">Avg Score</div>
        </div>
        <div className="bg-gradient-to-br from-[#6366F1] to-[#8B5CF6] rounded-lg p-6 text-center shadow-card text-white">
          <div className="text-3xl font-bold mb-1">{formatScore(topScore).replace("%", "")}</div>
          <div className="text-sm opacity-90">Top Score</div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="bg-white border border-[#E5E5E5] rounded-lg p-4 mb-6 flex items-center justify-between gap-4 shadow-card">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
            className="w-4 h-4 rounded border-[#E5E5E5] text-[#6366F1] focus:ring-[#6366F1]"
          />
          <span className="text-sm font-medium text-[#262626]">Compare Mode</span>
        </label>

        <div className="flex gap-2">
          <button
            onClick={() => setShowReRankModal(true)}
            className="flex items-center gap-2 px-4 py-2 border border-[#E5E5E5] rounded-lg text-[#262626] hover:bg-[#F5F5F5] transition-colors"
          >
            <RotateCcw size={16} />
            Re-rank
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <FiltersBar />

      {/* NER Testing Section */}
      {selectedFilename && collection_id && company_id && (
        <NERTestingSection
          collectionId={collection_id}
          companyId={company_id}
          selectedFilename={selectedFilename}
        />
      )}

      {/* Results Table */}
      {error && (
        <div className="bg-[#FEE2E2] border border-[#EF4444] rounded-lg p-4 mb-6 flex gap-3">
          <AlertCircle size={20} className="text-[#EF4444] flex-shrink-0" />
          <p className="text-sm text-[#DC2626]">{error}</p>
        </div>
      )}

      <ResultsTable candidates={candidates} onRowClick={setSelectedFilename} />

      {/* Selection Bar */}
      {compareMode && selectedForComparison.length > 0 && (
        <>
          <CompareSelectionBar
            selectedCount={selectedForComparison.length}
            onCompare={() => setShowComparisonModal(true)}
          />
        </>
      )}

      {/* Modals */}
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
