"use client"

import { X } from "lucide-react"
import type { RankedCandidate } from "@/types"
import { formatScore, getScoreBgColor, getScoreTextColor } from "@/utils/formatters"

interface ComparisonModalProps {
  candidates: RankedCandidate[]
  onClose: () => void
}

export function ComparisonModal({ candidates, onClose }: ComparisonModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-4xl w-full max-h-80vh overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
          <h2 className="text-xl font-bold text-gray-900">Compare Candidates</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X size={24} />
          </button>
        </div>

        <div className="grid gap-6 p-6" style={{ gridTemplateColumns: `repeat(${candidates.length}, 1fr)` }}>
          {candidates.map((candidate) => (
            <div key={candidate.filename} className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900 text-sm mb-4 break-words">{candidate.filename}</h3>

              <div className="space-y-4">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Final Score</p>
                  <div
                    className={`inline-block px-3 py-2 rounded font-bold text-lg ${getScoreBgColor(
                      candidate.final_score,
                    )} ${getScoreTextColor(candidate.final_score)}`}
                  >
                    {formatScore(candidate.final_score)}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-600 mb-2">Score Breakdown</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span>TF-IDF:</span>
                      <span className="font-medium">{formatScore(candidate.tfidf_score)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Skill:</span>
                      <span className="font-medium">{formatScore(candidate.skill_score)}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-600 mb-2">Matched Skills</p>
                  <div className="flex flex-wrap gap-1">
                    {candidate.explainability.matched_skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-block px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-gray-600 mb-2">Missing Skills</p>
                  <div className="flex flex-wrap gap-1">
                    {candidate.explainability.missing_skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-block px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full font-medium"
                      >
                        ⚠ {skill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
