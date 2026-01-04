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
    <div className="max-w-2xl mx-auto px-6 py-12">
      <h2 className="text-3xl font-bold text-gray-900 mb-8">Phase 1: Upload Resumes</h2>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Company ID</label>
          <input
            type="text"
            value={companyId}
            onChange={handleCompanyIdChange}
            placeholder="Enter company ID (e.g., acme, techcorp)"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Resume Collection (ZIP File)</label>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? "border-blue-600 bg-blue-50" : "border-gray-300 hover:border-gray-400"
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
              <Upload size={32} className="mx-auto mb-2 text-gray-400" />
              <p className="text-gray-700 font-medium">Drag and drop ZIP file here</p>
              <p className="text-gray-500 text-sm">or click to browse</p>
              <p className="text-gray-400 text-xs mt-2">Supported formats: .zip</p>
            </label>
          </div>
        </div>

        {zipFile && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-700">
              📄 {zipFile.name} ({formatFileSize(zipFile.size)})
            </p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-300 rounded-lg p-4 flex gap-3">
            <AlertCircle size={20} className="text-red-600 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <button
          onClick={handleCreateCollection}
          disabled={!companyId.trim() || !zipFile || loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Creating Collection..." : "Create Collection"}
        </button>
      </div>
    </div>
  )
}
