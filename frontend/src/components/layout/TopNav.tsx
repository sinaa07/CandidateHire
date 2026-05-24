"use client"

import { useState } from "react"
import Link from "next/link"
import { ChevronDown, FileStack } from "lucide-react"
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
    setIsDropdownOpen(false)
  }

  return (
    <nav className="sticky top-0 z-40 bg-card border-b border-border shadow-sm">
      <div className="px-6 h-16 flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg gradient-primary flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">R</span>
          </div>
          <div className="flex flex-col">
            <h1 className="text-lg font-bold text-foreground leading-tight">ResumeRanker</h1>
            <span className="text-xs text-muted-foreground hidden sm:block">HR Screening Dashboard</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/dashboard"
            className="hidden px-3 py-2 text-sm font-medium text-foreground hover:bg-muted rounded-lg transition-theme sm:inline-block"
          >
            Dashboard (v2)
          </Link>
          <div className="relative">
            <button
              onClick={handleCollectionsClick}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground hover:bg-muted rounded-lg transition-theme"
            >
              <FileStack size={16} className="text-muted-foreground" />
              <span>Collections</span>
              <ChevronDown
                size={16}
                className={`text-muted-foreground transition-transform ${isDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>

            {isDropdownOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setIsDropdownOpen(false)} />
                <div className="absolute top-full right-0 mt-2 bg-card border border-border rounded-xl shadow-lg min-w-72 overflow-hidden z-20">
                  <div className="p-2">
                    {collections.length > 0 ? (
                      <ul className="space-y-1">
                        {collections.map((collection) => (
                          <li key={collection.id}>
                            <button
                              onClick={() => handleSelectCollection(collection)}
                              className="w-full text-left px-3 py-2.5 text-sm rounded-lg hover:bg-muted transition-theme"
                            >
                              <div className="font-semibold text-foreground">{collection.company_id}</div>
                              <div className="text-xs text-muted-foreground font-mono mt-0.5">
                                {collection.id.substring(0, 20)}...
                              </div>
                              <div className="text-xs text-muted-foreground mt-1 capitalize">{collection.status}</div>
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="px-3 py-4 text-sm text-muted-foreground text-center">No collections yet</div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          <button
            onClick={handleNewCollection}
            className="px-4 py-2 gradient-primary text-white rounded-lg font-medium text-sm hover:opacity-90 transition-theme shadow-sm"
          >
            + New Collection
          </button>
        </div>
      </div>
    </nav>
  )
}
