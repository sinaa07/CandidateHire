"use client"

import type React from "react"
import { createContext, useContext, useState, useCallback } from "react"
import type { AppState, Phase } from "@/types"

interface AppContextType extends AppState {
  setPhase: (phase: Phase) => void
  setCollectionId: (id: string) => void
  setCompanyId: (id: string) => void
  setProcessingResults: (results: any) => void
  setRankingResults: (results: any) => void
  setFilters: (filters: any) => void
  setCompareMode: (enabled: boolean) => void
  toggleSelectedForComparison: (filename: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  resetState: () => void
}

const AppContext = createContext<AppContextType | undefined>(undefined)

const initialState: AppState = {
  currentCollection: {
    collection_id: null,
    company_id: null,
    phase: 1,
    status: {
      uploaded: false,
      processed: false,
      ranked: false,
    },
  },
  processingResults: null,
  rankingResults: {
    summary: null,
    candidates: [],
  },
  filters: {
    searchText: "",
    minScore: 0,
    maxScore: 100,
  },
  compareMode: false,
  selectedForComparison: [],
  loading: false,
  error: null,
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AppState>(initialState)

  const setPhase = useCallback((phase: Phase) => {
    setState((prev) => ({
      ...prev,
      currentCollection: { ...prev.currentCollection, phase },
    }))
  }, [])

  const setCollectionId = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      currentCollection: { ...prev.currentCollection, collection_id: id },
    }))
  }, [])

  const setCompanyId = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      currentCollection: { ...prev.currentCollection, company_id: id },
    }))
  }, [])

  const setProcessingResults = useCallback((results: any) => {
    setState((prev) => ({
      ...prev,
      processingResults: results,
      currentCollection: {
        ...prev.currentCollection,
        status: { ...prev.currentCollection.status, processed: true },
      },
    }))
  }, [])

  const setRankingResults = useCallback((results: any) => {
    setState((prev) => ({
      ...prev,
      rankingResults: results,
      currentCollection: {
        ...prev.currentCollection,
        status: { ...prev.currentCollection.status, ranked: true },
      },
    }))
  }, [])

  const setFilters = useCallback((filters: any) => {
    setState((prev) => ({
      ...prev,
      filters: { ...prev.filters, ...filters },
    }))
  }, [])

  const setCompareMode = useCallback((enabled: boolean) => {
    setState((prev) => ({
      ...prev,
      compareMode: enabled,
      selectedForComparison: enabled ? [] : prev.selectedForComparison,
    }))
  }, [])

  const toggleSelectedForComparison = useCallback((filename: string) => {
    setState((prev) => {
      const selected = prev.selectedForComparison
      if (selected.includes(filename)) {
        return {
          ...prev,
          selectedForComparison: selected.filter((f) => f !== filename),
        }
      } else if (selected.length < 3) {
        return {
          ...prev,
          selectedForComparison: [...selected, filename],
        }
      }
      return prev
    })
  }, [])

  const setLoading = useCallback((loading: boolean) => {
    setState((prev) => ({ ...prev, loading }))
  }, [])

  const setError = useCallback((error: string | null) => {
    setState((prev) => ({ ...prev, error }))
  }, [])

  const resetState = useCallback(() => {
    setState(initialState)
  }, [])

  return (
    <AppContext.Provider
      value={{
        ...state,
        setPhase,
        setCollectionId,
        setCompanyId,
        setProcessingResults,
        setRankingResults,
        setFilters,
        setCompareMode,
        toggleSelectedForComparison,
        setLoading,
        setError,
        resetState,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error("useAppContext must be used within AppProvider")
  }
  return context
}
