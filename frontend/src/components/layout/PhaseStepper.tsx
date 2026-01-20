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
    <div className="bg-white border-b border-[#E5E5E5] px-6 py-6">
      <div className="flex items-center justify-between mb-4">
        {PHASES.map((step, index) => {
          const isActive = step.number === phase
          const isCompleted = step.number < phase

          return (
            <div key={step.number} className="flex items-center flex-1">
              <button
                onClick={() => handleStepClick(step.number)}
                disabled={step.number > phase}
                className={`flex flex-col items-center gap-2 ${
                  step.number > phase ? "cursor-not-allowed" : "cursor-pointer"
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center font-bold transition-all ${
                    isActive
                      ? "bg-[#6366F1] text-white border-2 border-[#6366F1] shadow-lg scale-110"
                      : isCompleted
                        ? "bg-[#10B981] text-white border-2 border-[#10B981]"
                        : "bg-[#F5F5F5] text-[#737373] border-2 border-[#E5E5E5]"
                  }`}
                >
                  {isCompleted ? <CheckCircle2 size={24} /> : step.number}
                </div>
                <span className={`text-sm font-medium ${isActive ? "text-[#6366F1]" : isCompleted ? "text-[#10B981]" : "text-[#737373]"}`}>
                  {step.label}
                </span>
              </button>

              {index < PHASES.length - 1 && (
                <div className={`flex-1 h-1 mx-4 rounded-full transition-colors ${isCompleted ? "bg-[#10B981]" : "bg-[#E5E5E5]"}`} />
              )}
            </div>
          )
        })}
      </div>

      {collection_id && (
        <div className="text-xs text-[#737373] text-center font-mono">Collection ID: {collection_id.substring(0, 20)}...</div>
      )}
    </div>
  )
}
