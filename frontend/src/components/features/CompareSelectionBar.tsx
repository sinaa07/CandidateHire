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
    <div className="fixed bottom-0 left-0 right-0 bg-card border-t border-border shadow-lg p-4 z-30">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div>
          <span className="text-sm font-medium text-foreground">{selectedCount} candidates selected</span>
          <div className="mt-1 flex flex-wrap gap-2">
            {selectedForComparison.map((filename) => (
              <span
                key={filename}
                className="text-xs bg-muted px-2 py-1 rounded-md border border-border font-mono"
              >
                {filename.substring(0, 24)}...
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={onCompare}
          className="px-6 py-2.5 gradient-primary text-white rounded-lg font-medium hover:opacity-90 transition-theme shrink-0"
        >
          Compare
        </button>
      </div>
    </div>
  )
}
