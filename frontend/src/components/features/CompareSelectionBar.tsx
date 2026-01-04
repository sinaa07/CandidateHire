"use client"

import { useAppContext } from "@/contexts/AppContext"

interface CompareSelectionBarProps {
  selectedCount: number
  onCompare: () => void
}

export function CompareSelectionBar({ selectedCount, onCompare }: CompareSelectionBarProps) {
  const { selectedForComparison } = useAppContext()

  if (selectedCount === 0) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="text-sm text-gray-700">
          <span className="font-medium">Selected: {selectedCount} candidates</span>
          <div className="mt-1 flex gap-2">
            {selectedForComparison.map((filename) => (
              <span key={filename} className="text-xs bg-gray-100 px-2 py-1 rounded">
                {filename.substring(0, 20)}...
              </span>
            ))}
          </div>
        </div>

        <button
          onClick={onCompare}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Compare
        </button>
      </div>
    </div>
  )
}
