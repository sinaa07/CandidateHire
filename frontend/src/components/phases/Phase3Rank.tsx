"use client"

import type React from "react"

import { useState } from "react"
import { AlertCircle, CheckCircle2, UploadIcon, Loader } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { rankCollectionText, rankCollectionFile } from "@/utils/api"

export function Phase3Rank() {
  const { currentCollection, setRankingResults, setPhase, setLoading, setError, error, loading } = useAppContext()
  const { collection_id, company_id } = currentCollection

  const [mode, setMode] = useState<"text" | "file">("text")
  const [jdText, setJdText] = useState("")
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [topK, setTopK] = useState("")
  const [isCompleted, setIsCompleted] = useState(false)
  const [rankingCount, setRankingCount] = useState(0)
  const [dragActive, setDragActive] = useState(false)

  const canSubmit = (mode === "text" && jdText.trim()) || (mode === "file" && jdFile)

  const handleRank = async () => {
    if (!collection_id || !company_id) {
      setError("Missing collection or company ID")
      return
    }

    if (!canSubmit) {
      setError("Please provide job description")
      return
    }

    setLoading(true)
    setError(null)

    try {
      const topKNum = topK ? Number.parseInt(topK) : undefined

      let response
      if (mode === "text") {
        response = await rankCollectionText(collection_id, company_id, jdText, topKNum)
      } else {
        if (!jdFile) throw new Error("No file selected")
        response = await rankCollectionFile(collection_id, company_id, jdFile, topKNum)
      }

      setRankingResults({
        summary: {
          resume_count: response.details?.resume_count || 0,
          ranked_count: response.details?.ranked_count || 0,
        },
        candidates: [],
      })

      setRankingCount(response.details?.ranked_count || 0)
      setIsCompleted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rank candidates")
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = (file: File) => {
    const validTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ]
    if (validTypes.includes(file.type) || file.name.match(/\.(pdf|docx|txt)$/i)) {
      setJdFile(file)
      setError(null)
    } else {
      setError("Please select a valid file (.pdf, .docx, .txt)")
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

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <h2 className="text-3xl font-bold text-gray-900 mb-8">Phase 3: Rank Candidates</h2>

      {!isCompleted && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-3">Job Description</label>
            <div className="flex gap-2 bg-gray-50 p-2 rounded-lg w-fit">
              <button
                onClick={() => setMode("text")}
                className={`px-4 py-2 rounded transition-colors ${
                  mode === "text" ? "bg-white border border-gray-300" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Paste Text
              </button>
              <button
                onClick={() => setMode("file")}
                className={`px-4 py-2 rounded transition-colors ${
                  mode === "file" ? "bg-white border border-gray-300" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Upload File
              </button>
            </div>
          </div>

          {mode === "text" && (
            <textarea
              value={jdText}
              onChange={(e) => {
                setJdText(e.target.value)
                setError(null)
              }}
              placeholder="Enter or paste the job description here..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent min-h-48 resize-vertical"
            />
          )}

          {mode === "file" && (
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
                accept=".pdf,.docx,.txt"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                className="hidden"
                id="jd-upload"
              />
              <label htmlFor="jd-upload" className="cursor-pointer block">
                <UploadIcon size={32} className="mx-auto mb-2 text-gray-400" />
                <p className="text-gray-700 font-medium">Drag and drop JD file here</p>
                <p className="text-gray-500 text-sm">or click to browse</p>
                <p className="text-gray-400 text-xs mt-2">Supported: .pdf, .docx, .txt</p>
              </label>
            </div>
          )}

          {jdFile && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-700">📄 {jdFile.name}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">Top K Candidates (Optional)</label>
            <input
              type="number"
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              placeholder="e.g., 10"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">Leave empty to rank all candidates</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-300 rounded-lg p-4 flex gap-3">
              <AlertCircle size={20} className="text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <button
            onClick={handleRank}
            disabled={!canSubmit || loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader size={20} className="animate-spin" />
                Ranking...
              </>
            ) : (
              "Rank Candidates"
            )}
          </button>
        </div>
      )}

      {isCompleted && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-green-700 bg-green-50 p-4 rounded-lg border border-green-200">
            <CheckCircle2 size={24} />
            <span className="font-medium">Ranking Complete - {rankingCount} candidates ranked</span>
          </div>

          <button
            onClick={() => setPhase(4)}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
            View Results
            <span>→</span>
          </button>
        </div>
      )}
    </div>
  )
}
