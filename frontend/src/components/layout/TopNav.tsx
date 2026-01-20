"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { getCollectionsFromStorage } from "@/utils/storage"
import type { Collection } from "@/types"

export function TopNav() {
  const { setPhase, setCollectionId, setCompanyId, resetState } = useAppContext()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [collections, setCollections] = useState<Collection[]>([])

  const handleCollectionsClick = () => {
    const stored = getCollectionsFromStorage()
    setCollections(stored)
    setIsDropdownOpen(!isDropdownOpen)
  }

  const handleSelectCollection = (collection: Collection) => {
    setCollectionId(collection.id)
    setCompanyId(collection.company_id)
    setPhase(4)
    setIsDropdownOpen(false)
  }

  const handleNewCollection = () => {
    resetState()
    setPhase(1)
  }

  return (
    <nav className="sticky top-0 z-40 bg-white border-b border-[#E5E5E5] px-6 h-16 flex items-center justify-between shadow-card">
      <h1 className="text-2xl font-bold bg-gradient-to-r from-[#6366F1] to-[#8B5CF6] bg-clip-text text-transparent">
        ResumeRanker
      </h1>

      <div className="flex items-center gap-4">
        <div className="relative">
          <button
            onClick={handleCollectionsClick}
            className="flex items-center gap-2 px-3 py-2 text-[#262626] hover:bg-[#F5F5F5] rounded-md transition-colors text-sm font-medium"
          >
            Collections
            <ChevronDown size={16} />
          </button>

          {isDropdownOpen && (
            <div className="absolute top-full right-0 mt-2 bg-white border border-[#E5E5E5] rounded-lg shadow-modal min-w-64">
              {collections.length > 0 ? (
                <ul className="py-2">
                  {collections.map((collection) => (
                    <li key={collection.id}>
                      <button
                        onClick={() => handleSelectCollection(collection)}
                        className="w-full text-left px-4 py-2 text-sm text-[#262626] hover:bg-[#F5F5F5] transition-colors"
                      >
                        <div className="font-medium text-[#262626]">{collection.company_id}</div>
                        <div className="text-xs text-[#737373]">{collection.id.substring(0, 12)}...</div>
                        <div className="text-xs text-[#737373] capitalize">{collection.status}</div>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="px-4 py-2 text-sm text-[#737373]">No collections yet</div>
              )}
            </div>
          )}
        </div>

        <button
          onClick={handleNewCollection}
          className="px-4 py-2 gradient-primary text-white rounded-lg hover:opacity-90 transition-all font-medium shadow-card hover:shadow-lg hover:-translate-y-0.5"
        >
          + New Collection
        </button>
      </div>
    </nav>
  )
}
