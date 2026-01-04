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
    <div className="bg-white border-b border-gray-200 px-6 py-8">
      <div className="flex items-center justify-between mb-4">
        {PHASES.map((step, index) => {
          const isActive = step.number === phase
          const isCompleted = step.number < phase

          return (
            <div key={step.number} className="flex items-center">
              <button
                onClick={() => handleStepClick(step.number)}
                disabled={step.number > phase}
                className={`flex flex-col items-center gap-2 ${
                  step.number > phase ? "cursor-not-allowed" : "cursor-pointer"
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center font-bold transition-colors ${
                    isActive
                      ? "bg-blue-600 text-white border-2 border-blue-600"
                      : isCompleted
                        ? "bg-green-500 text-white border-2 border-green-500"
                        : "bg-gray-100 text-gray-400 border-2 border-gray-200"
                  }`}
                >
                  {isCompleted ? <CheckCircle2 size={24} /> : step.number}
                </div>
                <span className={`text-sm font-medium ${isActive ? "text-blue-600" : "text-gray-600"}`}>
                  {step.label}
                </span>
              </button>

              {index < PHASES.length - 1 && (
                <div className={`flex-1 h-1 mx-4 ${isCompleted ? "bg-green-500" : "bg-gray-200"}`} />
              )}
            </div>
          )
        })}
      </div>

      {collection_id && (
        <div className="text-xs text-gray-500 text-center">Collection ID: {collection_id.substring(0, 20)}...</div>
      )}
    </div>
  )
}
