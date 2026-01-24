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

    // Apply search filter
    if (filters.searchText) {
      result = result.filter((c) => c.filename.toLowerCase().includes(filters.searchText.toLowerCase()))
    }

    // Apply score range filter
    const minScore = filters.minScore / 100
    const maxScore = filters.maxScore / 100
    result = result.filter((c) => c.final_score >= minScore && c.final_score <= maxScore)

    // Apply sorting
    if (sortBy === "score") {
      result.sort((a, b) => b.final_score - a.final_score)
    }

    return result
  }, [candidates, filters, sortBy])

  const totalPages = Math.ceil(filtered.length / itemsPerPage)
  const paginatedData = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  return (
    <div className="space-y-4">
      <div className="bg-white border border-[#E5E5E5] rounded-lg overflow-hidden shadow-card">
        <table className="w-full">
          <thead>
            <tr className="bg-[#F5F5F5] border-b border-[#E5E5E5]">
              {compareMode && <th className="px-4 py-3 text-left w-12" />}
              <th
                onClick={() => setSortBy("rank")}
                className="px-4 py-3 text-left font-semibold text-[#262626] cursor-pointer hover:bg-[#E5E5E5] w-16 transition-colors"
              >
                Rank
              </th>
              <th className="px-4 py-3 text-left font-semibold text-[#262626] w-48">Filename</th>
              <th
                onClick={() => setSortBy("score")}
                className="px-4 py-3 text-left font-semibold text-[#262626] cursor-pointer hover:bg-[#E5E5E5] w-32 transition-colors"
              >
                Score
              </th>
              <th className="px-4 py-3 text-left font-semibold text-[#262626]">Matched Skills</th>
              <th className="px-4 py-3 text-left font-semibold text-[#262626]">Missing Skills</th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((candidate, idx) => (
              <tr
                key={candidate.filename}
                onClick={() => onRowClick?.(candidate.filename)}
                className={`border-b border-[#E5E5E5] ${idx % 2 === 0 ? "bg-white" : "bg-[#F5F5F5]"} hover:bg-[#EEF2FF] transition-colors ${onRowClick ? "cursor-pointer" : ""}`}
              >
                {compareMode && (
                  <td className="px-4 py-4 text-center">
                    <input
                      type="checkbox"
                      checked={selectedForComparison.includes(candidate.filename)}
                      onChange={() => toggleSelectedForComparison(candidate.filename)}
                      disabled={
                        selectedForComparison.length >= 3 && !selectedForComparison.includes(candidate.filename)
                      }
                      className="w-4 h-4 rounded border-[#E5E5E5] text-[#6366F1] focus:ring-[#6366F1] cursor-pointer"
                    />
                  </td>
                )}
                <td className="px-4 py-4 font-semibold text-[#262626]">{candidate.rank}</td>
                <td className="px-4 py-4 text-[#262626] text-sm font-mono" title={candidate.filename}>
                  {truncateFilename(candidate.filename)}
                </td>
                <td className="px-4 py-4">
                  <div
                    className={`inline-block px-3 py-1 rounded-lg font-semibold text-sm ${getScoreBgColor(
                      candidate.final_score,
                    )} ${getScoreTextColor(candidate.final_score)}`}
                  >
                    {formatScore(candidate.final_score)}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1">
                    {candidate.explainability.matched_skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-block px-2 py-1 bg-[#ECFDF5] text-[#10B981] text-xs rounded-full font-medium border border-[#10B981]"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1">
                    {candidate.explainability.missing_skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-block px-2 py-1 bg-[#FEE2E2] text-[#EF4444] text-xs rounded-full font-medium border border-[#EF4444]"
                      >
                        ⚠ {skill}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between bg-white border border-[#E5E5E5] rounded-lg p-4 shadow-card">
        <div className="text-sm text-[#737373]">
          Showing {paginatedData.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0} to{" "}
          {Math.min(currentPage * itemsPerPage, filtered.length)} of {filtered.length}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border border-[#E5E5E5] rounded-lg text-sm hover:bg-[#F5F5F5] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i + 1}
              onClick={() => setCurrentPage(i + 1)}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                currentPage === i + 1
                  ? "bg-[#6366F1] text-white"
                  : "border border-[#E5E5E5] hover:bg-[#F5F5F5] text-[#262626]"
              }`}
            >
              {i + 1}
            </button>
          ))}
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border border-[#E5E5E5] rounded-lg text-sm hover:bg-[#F5F5F5] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
