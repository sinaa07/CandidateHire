"use client"

import { useState, useEffect } from "react"
import { Loader, ChevronDown, ChevronUp, TestTube } from "lucide-react"
import { getResumeEntities } from "@/utils/api"
import type { EntitiesResponse } from "@/utils/api"

interface NERTestingSectionProps {
  collectionId: string
  companyId: string
  selectedFilename: string | null
}

export function NERTestingSection({
  collectionId,
  companyId,
  selectedFilename,
}: NERTestingSectionProps) {
  const [entities, setEntities] = useState<EntitiesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    if (!selectedFilename || !collectionId || !companyId) {
      setEntities(null)
      setError(null)
      return
    }

    const fetchEntities = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await getResumeEntities(collectionId, selectedFilename, companyId)
        setEntities(data)
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load entities"
        // Provide more helpful error message
        if (errorMessage.includes("not found") || errorMessage.includes("Entities file")) {
          setError(
            `NER data not found for "${selectedFilename}". ` +
            `This may happen if: (1) Processing didn't extract entities, (2) File wasn't processed, or (3) Filename mismatch. ` +
            `Error: ${errorMessage}`
          )
        } else {
          setError(errorMessage)
        }
        setEntities(null)
      } finally {
        setLoading(false)
      }
    }

    fetchEntities()
  }, [selectedFilename, collectionId, companyId])

  if (!selectedFilename) {
    return null
  }

  return (
    <div className="bg-white border border-[#E5E5E5] rounded-lg shadow-card mb-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-[#F5F5F5] transition-colors"
      >
        <div className="flex items-center gap-2">
          <TestTube size={18} className="text-[#6366F1]" />
          <span className="text-sm font-medium text-[#262626]">NER Testing (Testing Only)</span>
        </div>
        {isExpanded ? (
          <ChevronUp size={18} className="text-[#737373]" />
        ) : (
          <ChevronDown size={18} className="text-[#737373]" />
        )}
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 border-t border-[#E5E5E5]">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader size={20} className="text-[#6366F1] animate-spin" />
            </div>
          )}

          {error && (
            <div className="bg-[#FEE2E2] border border-[#EF4444] rounded-lg p-3 mt-4">
              <p className="text-sm text-[#DC2626]">{error}</p>
            </div>
          )}

          {entities && !loading && (
            <div className="mt-4 space-y-4">
              {/* Skills */}
              <div>
                <h4 className="text-sm font-semibold text-[#262626] mb-2">Skills</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(entities.entities.skills).length > 0 ? (
                    Object.entries(entities.entities.skills).map(([skill, info]) => (
                      <div
                        key={skill}
                        className="bg-[#EEF2FF] border border-[#C7D2FE] rounded px-2 py-1 text-xs text-[#4338CA]"
                      >
                        {skill} ({info.count})
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-[#737373]">No skills found</span>
                  )}
                </div>
              </div>

              {/* Roles */}
              <div>
                <h4 className="text-sm font-semibold text-[#262626] mb-2">Roles</h4>
                <div className="flex flex-wrap gap-2">
                  {entities.entities.roles.length > 0 ? (
                    entities.entities.roles.map((role, idx) => (
                      <div
                        key={idx}
                        className="bg-[#F0FDF4] border border-[#BBF7D0] rounded px-2 py-1 text-xs text-[#166534]"
                      >
                        {role}
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-[#737373]">No roles found</span>
                  )}
                </div>
              </div>

              {/* Organizations */}
              <div>
                <h4 className="text-sm font-semibold text-[#262626] mb-2">Organizations</h4>
                <div className="flex flex-wrap gap-2">
                  {entities.entities.organizations.length > 0 ? (
                    entities.entities.organizations.map((org, idx) => (
                      <div
                        key={idx}
                        className="bg-[#FEF3C7] border border-[#FDE68A] rounded px-2 py-1 text-xs text-[#92400E]"
                      >
                        {org}
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-[#737373]">No organizations found</span>
                  )}
                </div>
              </div>

              {/* Locations */}
              <div>
                <h4 className="text-sm font-semibold text-[#262626] mb-2">Locations</h4>
                <div className="flex flex-wrap gap-2">
                  {entities.entities.locations.length > 0 ? (
                    entities.entities.locations.map((location, idx) => (
                      <div
                        key={idx}
                        className="bg-[#FCE7F3] border border-[#FBCFE8] rounded px-2 py-1 text-xs text-[#9F1239]"
                      >
                        {location}
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-[#737373]">No locations found</span>
                  )}
                </div>
              </div>

              {/* Education */}
              <div>
                <h4 className="text-sm font-semibold text-[#262626] mb-2">Education</h4>
                <div className="text-xs text-[#737373] space-y-1">
                  {entities.entities.education.degree && (
                    <div>Degree: {entities.entities.education.degree}</div>
                  )}
                  {entities.entities.education.field && (
                    <div>Field: {entities.entities.education.field}</div>
                  )}
                  {!entities.entities.education.degree && !entities.entities.education.field && (
                    <span>No education info found</span>
                  )}
                </div>
              </div>

              {/* Experience */}
              <div>
                <h4 className="text-sm font-semibold text-[#262626] mb-2">Experience</h4>
                <div className="text-xs text-[#737373] space-y-1">
                  {entities.entities.experience.years_min !== null && (
                    <div>Years (min): {entities.entities.experience.years_min}</div>
                  )}
                  {entities.entities.experience.years_max !== null && (
                    <div>Years (max): {entities.entities.experience.years_max}</div>
                  )}
                  {entities.entities.experience.earliest_date && (
                    <div>Earliest: {entities.entities.experience.earliest_date}</div>
                  )}
                  {entities.entities.experience.latest_date && (
                    <div>Latest: {entities.entities.experience.latest_date}</div>
                  )}
                  {entities.entities.experience.years_min === null &&
                    entities.entities.experience.years_max === null &&
                    !entities.entities.experience.earliest_date &&
                    !entities.entities.experience.latest_date && (
                      <span>No experience info found</span>
                    )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
