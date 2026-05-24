"use client"

import type React from "react"
import { useState } from "react"
import { Upload, AlertCircle, X, Package } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { createCollection } from "@/utils/api"
import { saveCollectionToStorage } from "@/utils/storage"
import { formatFileSize } from "@/utils/formatters"

export function Phase1Upload() {
  const { setCollectionId, setCompanyId, setPhase, setLoading, setError, error, loading } = useAppContext()

  const [companyId, setLocalCompanyId] = useState("")
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileSelect = (file: File) => {
    if (file.name.endsWith(".zip")) {
      setZipFile(file)
      setError(null)
    } else {
      setError("Please select a valid ZIP file")
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const files = e.dataTransfer.files
    if (files?.[0]) handleFileSelect(files[0])
  }

  const handleCreateCollection = async () => {
    if (!companyId.trim() || !zipFile) {
      setError("Please fill in all fields")
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await createCollection(companyId, zipFile)
      setCollectionId(response.collection_id)
      setCompanyId(companyId)
      saveCollectionToStorage({
        id: response.collection_id,
        company_id: companyId,
        created_at: new Date().toISOString(),
        status: "uploaded",
        last_accessed: new Date().toISOString(),
      })
      setPhase(2)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create collection")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-6 py-10 max-w-2xl mx-auto">
      <header className="mb-8">
        <h2 className="text-2xl font-bold text-foreground">Collection Upload</h2>
        <p className="text-muted-foreground mt-1">
          Upload a ZIP of resumes and assign a company ID to start screening.
        </p>
      </header>

      <div className="space-y-6">
        <div className="dashboard-card p-6">
          <label className="block text-sm font-semibold text-foreground mb-2">Company ID</label>
          <input
            type="text"
            value={companyId}
            onChange={(e) => {
              setLocalCompanyId(e.target.value)
              setError(null)
            }}
            placeholder="Enter company ID (e.g., acme, techcorp)"
            className="dashboard-input"
          />
        </div>

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`relative rounded-xl border-2 border-dashed px-6 py-16 text-center transition-theme cursor-pointer ${
            dragActive
              ? "border-primary bg-primary-50"
              : "border-border bg-card hover:border-primary hover:bg-primary-50/50"
          }`}
        >
          <input
            type="file"
            accept=".zip"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            className="hidden"
            id="zip-upload"
          />
          <label htmlFor="zip-upload" className="cursor-pointer flex flex-col items-center gap-4">
            <div
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-theme ${
                dragActive ? "bg-primary text-white" : "bg-muted text-primary"
              }`}
            >
              <Upload size={32} />
            </div>
            <div>
              <p className="text-foreground font-semibold text-lg">Drop ZIP or Browse</p>
              <p className="text-muted-foreground text-sm mt-1">Supported formats: .zip</p>
            </div>
          </label>
        </div>

        {zipFile && (
          <div className="dashboard-card p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                <Package size={20} className="text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{zipFile.name}</p>
                <p className="text-xs text-muted-foreground">{formatFileSize(zipFile.size)}</p>
              </div>
            </div>
            <button
              onClick={() => setZipFile(null)}
              className="p-2 text-muted-foreground hover:text-error hover:bg-error-50 rounded-lg transition-theme"
              aria-label="Remove file"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {error && (
          <div className="bg-error-50 border border-error-100 rounded-lg p-4 flex gap-3">
            <AlertCircle size={20} className="text-error shrink-0" />
            <p className="text-sm text-error font-medium">{error}</p>
          </div>
        )}

        <button
          onClick={handleCreateCollection}
          disabled={!companyId.trim() || !zipFile || loading}
          className="btn-primary flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Creating Collection...
            </>
          ) : (
            <>Create Collection →</>
          )}
        </button>
      </div>
    </div>
  )
}
