"use client"

import type React from "react"

import { useState } from "react"
import { Upload, AlertCircle } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { createCollection } from "@/utils/api"
import { saveCollectionToStorage } from "@/utils/storage"
import { formatFileSize } from "@/utils/formatters"

export function Phase1Upload() {
  const { setCollectionId, setCompanyId, setPhase, setLoading, setError, error, loading } = useAppContext()

  const [companyId, setLocalCompanyId] = useState("")
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleCompanyIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalCompanyId(e.target.value)
    setError(null)
  }

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
    if (files?.[0]) {
      handleFileSelect(files[0])
    }
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
      const collectionId = response.collection_id

      setCollectionId(collectionId)
      setCompanyId(companyId)

      saveCollectionToStorage({
        id: collectionId,
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
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold text-[#262626] mb-3">Upload Resume Collection</h2>
        <p className="text-[#737373]">Upload your resume collection as a ZIP file</p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-[#262626] mb-2">Company ID</label>
          <input
            type="text"
            value={companyId}
            onChange={handleCompanyIdChange}
            placeholder="Enter company ID (e.g., acme, techcorp)"
            className="w-full px-4 py-3 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6366F1] focus:border-transparent bg-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#262626] mb-2">Resume Collection (ZIP File)</label>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-all ${
              dragActive ? "border-[#6366F1] bg-[#EEF2FF]" : "border-[#E5E5E5] hover:border-[#6366F1] bg-white"
            }`}
          >
            <input
              type="file"
              accept=".zip"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              className="hidden"
              id="zip-upload"
            />
            <label htmlFor="zip-upload" className="cursor-pointer block">
              <Upload size={48} className={`mx-auto mb-4 ${dragActive ? "text-[#6366F1]" : "text-[#737373]"}`} />
              <p className="text-[#262626] font-semibold text-lg mb-1">Drop ZIP or Browse</p>
              <p className="text-[#737373] text-sm">Supported formats: .zip</p>
            </label>
          </div>
        </div>

        {zipFile && (
          <div className="bg-white border border-[#E5E5E5] rounded-lg p-4 shadow-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#10B981] rounded-lg flex items-center justify-center">
                  <span className="text-white text-xl">📦</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#262626]">{zipFile.name}</p>
                  <p className="text-xs text-[#737373]">{formatFileSize(zipFile.size)}</p>
                </div>
              </div>
              <button
                onClick={() => setZipFile(null)}
                className="text-[#737373] hover:text-[#262626] transition-colors"
              >
                <AlertCircle size={20} />
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-[#FEE2E2] border border-[#EF4444] rounded-lg p-4 flex gap-3">
            <AlertCircle size={20} className="text-[#EF4444] flex-shrink-0" />
            <p className="text-sm text-[#DC2626]">{error}</p>
          </div>
        )}

        <button
          onClick={handleCreateCollection}
          disabled={!companyId.trim() || !zipFile || loading}
          className="w-full gradient-primary text-white py-4 rounded-lg font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-card hover:shadow-lg hover:-translate-y-0.5"
        >
          {loading ? "Creating Collection..." : "Create Collection →"}
        </button>
      </div>
    </div>
  )
}
