"use client"

import { CheckCircle2 } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import type { Phase } from "@/types"

const PHASES = [
  { number: 1, label: "Upload" },
  { number: 2, label: "Process" },
  { number: 3, label: "Rank" },
  { number: 4, label: "Results" },
] as const

export function PhaseStepper() {
  const { currentCollection, setPhase } = useAppContext()
  const { phase, collection_id } = currentCollection

  const handleStepClick = (stepNumber: Phase) => {
    if (stepNumber < phase) {
      setPhase(stepNumber)
    }
  }

  return (
    <div className="bg-card border-b border-border">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between">
          {PHASES.map((step, index) => {
            const isActive = step.number === phase
            const isCompleted = step.number < phase
            const isUpcoming = step.number > phase

            return (
              <div key={step.number} className="flex items-center flex-1">
                <button
                  onClick={() => handleStepClick(step.number)}
                  disabled={isUpcoming}
                  className={`flex flex-col items-center gap-2 group ${
                    isUpcoming ? "cursor-not-allowed" : "cursor-pointer"
                  }`}
                >
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center font-semibold text-sm transition-all duration-300 ${
                      isActive
                        ? "bg-primary text-white border-2 border-primary shadow-md scale-105"
                        : isCompleted
                          ? "bg-success text-white border-2 border-success"
                          : "bg-muted text-muted-foreground border-2 border-border"
                    }`}
                  >
                    {isCompleted ? <CheckCircle2 size={20} /> : step.number}
                  </div>
                  <span
                    className={`text-sm font-medium transition-colors ${
                      isActive
                        ? "text-primary"
                        : isCompleted
                          ? "text-success"
                          : "text-muted-foreground"
                    }`}
                  >
                    {step.label}
                  </span>
                </button>

                {index < PHASES.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-4 rounded-full transition-all duration-500 ${
                      isCompleted ? "bg-success" : "bg-border"
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>

        {collection_id && (
          <div className="mt-4 text-center">
            <span className="text-xs text-muted-foreground font-mono bg-muted px-4 py-2 rounded-lg border border-border inline-block">
              Collection ID: {collection_id.substring(0, 24)}...
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
