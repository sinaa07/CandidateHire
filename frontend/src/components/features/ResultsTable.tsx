"use client"

import { useState, useMemo } from "react"
import { useAppContext } from "@/contexts/AppContext"
import type { RankedCandidate } from "@/types"
import { formatScore, getScoreBgColor, getScoreTextColor, truncateFilename } from "@/utils/formatters"

interface ResultsTableProps {
  candidates: RankedCandidate[]
  onRowClick?: (filename: string) => void
}

export function ResultsTable({ candidates, onRowClick }: ResultsTableProps) {
  const { compareMode, selectedForComparison, toggleSelectedForComparison, filters } = useAppContext()
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<"rank" | "score">("rank")
  const itemsPerPage = 10

  const filtered = useMemo(() => {
    let result = [...candidates]
    if (filters.searchText) {
      result = result.filter((c) =>
        c.filename.toLowerCase().includes(filters.searchText.toLowerCase()),
      )
    }
    const minScore = filters.minScore / 100
    const maxScore = filters.maxScore / 100
    result = result.filter((c) => c.final_score >= minScore && c.final_score <= maxScore)
    if (sortBy === "score") {
      result.sort((a, b) => b.final_score - a.final_score)
    }
    return result
  }, [candidates, filters, sortBy])

  const totalPages = Math.max(1, Math.ceil(filtered.length / itemsPerPage))
  const paginatedData = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  return (
    <div className="space-y-4 pb-20">
      <div className="dashboard-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead>
              <tr className="bg-muted border-b border-border">
                {compareMode && <th className="px-4 py-3 w-12" />}
                <th
                  onClick={() => setSortBy("rank")}
                  className="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wide cursor-pointer hover:bg-muted/80 w-16"
                >
                  Rank
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wide w-48">
                  Filename
                </th>
                <th
                  onClick={() => setSortBy("score")}
                  className="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wide cursor-pointer hover:bg-muted/80 w-28"
                >
                  Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wide">
                  Matched Skills
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wide">
                  Missing Skills
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((candidate, idx) => (
                <tr
                  key={candidate.filename}
                  onClick={() => onRowClick?.(candidate.filename)}
                  className={`border-b border-border transition-colors ${
                    idx % 2 === 0 ? "bg-card" : "bg-muted/30"
                  } hover:bg-primary-50 ${onRowClick ? "cursor-pointer" : ""}`}
                >
                  {compareMode && (
                    <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedForComparison.includes(candidate.filename)}
                        onChange={() => toggleSelectedForComparison(candidate.filename)}
                        disabled={
                          selectedForComparison.length >= 3 &&
                          !selectedForComparison.includes(candidate.filename)
                        }
                        className="w-4 h-4 rounded accent-primary cursor-pointer"
                      />
                    </td>
                  )}
                  <td className="px-4 py-3 font-semibold text-foreground">{candidate.rank}</td>
                  <td className="px-4 py-3 text-sm font-mono text-foreground" title={candidate.filename}>
                    {truncateFilename(candidate.filename)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-3 py-1 rounded-lg font-semibold text-sm ${getScoreBgColor(
                        candidate.final_score,
                      )} ${getScoreTextColor(candidate.final_score)}`}
                    >
                      {formatScore(candidate.final_score)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {candidate.explainability.matched_skills.map((skill) => (
                        <span
                          key={skill}
                          className="inline-block px-2 py-0.5 bg-success-50 text-success text-xs rounded-full font-medium border border-success/30"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {candidate.explainability.missing_skills.map((skill) => (
                        <span
                          key={skill}
                          className="inline-block px-2 py-0.5 bg-error-50 text-error text-xs rounded-full font-medium border border-error/30"
                        >
                          ⚠ {skill}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {paginatedData.length === 0 && (
                <tr>
                  <td colSpan={compareMode ? 6 : 5} className="px-4 py-12 text-center text-muted-foreground text-sm">
                    No candidates match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="dashboard-card px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          Showing {filtered.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1} to{" "}
          {Math.min(currentPage * itemsPerPage, filtered.length)} of {filtered.length}
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="btn-secondary text-sm disabled:opacity-50"
          >
            Previous
          </button>
          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i + 1}
              onClick={() => setCurrentPage(i + 1)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-theme ${
                currentPage === i + 1
                  ? "bg-primary text-white"
                  : "border border-border hover:bg-muted text-foreground"
              }`}
            >
              {i + 1}
            </button>
          ))}
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages || filtered.length === 0}
            className="btn-secondary text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
