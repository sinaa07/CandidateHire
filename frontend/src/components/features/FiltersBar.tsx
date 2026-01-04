"use client"
import { Search, X } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"

export function FiltersBar() {
  const { filters, setFilters } = useAppContext()

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 space-y-4">
      <div className="flex gap-4 flex-wrap items-end">
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-medium text-gray-700 mb-1">Search by filename</label>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={filters.searchText}
              onChange={(e) => setFilters({ searchText: e.target.value })}
              placeholder="Search filename..."
              className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>
        </div>

        <div className="w-40">
          <label className="block text-xs font-medium text-gray-700 mb-1">Score Range (%)</label>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              max="100"
              value={filters.minScore}
              onChange={(e) => setFilters({ minScore: Number.parseInt(e.target.value) || 0 })}
              placeholder="Min"
              className="w-20 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
            <input
              type="number"
              min="0"
              max="100"
              value={filters.maxScore}
              onChange={(e) => setFilters({ maxScore: Number.parseInt(e.target.value) || 100 })}
              placeholder="Max"
              className="w-20 px-2 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>
        </div>

        <button
          onClick={() => setFilters({ searchText: "", minScore: 0, maxScore: 100 })}
          className="flex items-center gap-2 px-3 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
        >
          <X size={16} />
          Clear
        </button>
      </div>
    </div>
  )
}
