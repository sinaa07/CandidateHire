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
    setPhase(1)
    setIsDropdownOpen(false)
  }

  const handleNewCollection = () => {
    resetState()
    setPhase(1)
  }

  return (
    <nav className="sticky top-0 z-40 bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">CandidateHire</h1>

        <div className="flex items-center gap-4">
          <div className="relative">
            <button
              onClick={handleCollectionsClick}
              className="flex items-center gap-2 px-3 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              Collections
              <ChevronDown size={16} />
            </button>

            {isDropdownOpen && (
              <div className="absolute top-full right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg min-w-64">
                {collections.length > 0 ? (
                  <ul className="py-2">
                    {collections.map((collection) => (
                      <li key={collection.id}>
                        <button
                          onClick={() => handleSelectCollection(collection)}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                          <div className="font-medium text-gray-900">{collection.company_id}</div>
                          <div className="text-xs text-gray-500">{collection.id.substring(0, 12)}...</div>
                          <div className="text-xs text-gray-400 capitalize">{collection.status}</div>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="px-4 py-2 text-sm text-gray-500">No collections yet</div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={handleNewCollection}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
          >
            + New Collection
          </button>
        </div>
      </div>
    </nav>
  )
}
