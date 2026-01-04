"use client"

import type React from "react"

import { useState } from "react"
import { X, AlertCircle } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { rankCollectionText, rankCollectionFile, getReport } from "@/utils/api"

interface ReRankModalProps {
  onClose: () => void
}

export function ReRankModal({ onClose }: ReRankModalProps) {
  const { currentCollection, setRankingResults, setLoading, setError } = useAppContext()
  const { collection_id, company_id } = currentCollection

  const [mode, setMode] = useState<"text" | "file">("text")
  const [jdText, setJdText] = useState("")
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [topK, setTopK] = useState("")
  const [error, setLocalError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const canSubmit = (mode === "text" && jdText.trim()) || (mode === "file" && jdFile)

  const handleFileSelect = (file: File) => {
    const validTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ]
    if (validTypes.includes(file.type) || file.name.match(/\.(pdf|docx|txt)$/i)) {
      setJdFile(file)
      setLocalError(null)
    } else {
      setLocalError("Please select a valid file (.pdf, .docx, .txt)")
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

  const handleRankAgain = async () => {
    if (!collection_id || !company_id) {
      setLocalError("Missing collection or company ID")
      return
    }

    if (!canSubmit) {
      setLocalError("Please provide job description")
      return
    }

    setLoading(true)
    setLocalError(null)
    setError(null)

    try {
      const topKNum = topK ? Number.parseInt(topK) : undefined

      if (mode === "text") {
        await rankCollectionText(collection_id, company_id, jdText, topKNum)
      } else {
        if (!jdFile) throw new Error("No file selected")
        await rankCollectionFile(collection_id, company_id, jdFile, topKNum)
      }

      // Refresh report
      const report = await getReport(collection_id, company_id)
      const candidates = report.phase3?.ranking_results || []
      setRankingResults({
        summary: report.phase3?.ranking_summary || { resume_count: 0, ranked_count: 0 },
        candidates,
      })

      onClose()
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Failed to re-rank candidates")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Re-rank with Different JD</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-3">Job Description</label>
            <div className="flex gap-2 bg-gray-50 p-2 rounded-lg w-fit">
              <button
                onClick={() => setMode("text")}
                className={`px-4 py-2 rounded text-sm transition-colors ${
                  mode === "text" ? "bg-white border border-gray-300" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Paste Text
              </button>
              <button
                onClick={() => setMode("file")}
                className={`px-4 py-2 rounded text-sm transition-colors ${
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
                setLocalError(null)
              }}
              placeholder="Enter or paste job description..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent min-h-32 resize-vertical text-sm"
            />
          )}

          {mode === "file" && (
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                dragActive ? "border-blue-600 bg-blue-50" : "border-gray-300 hover:border-gray-400"
              }`}
            >
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                className="hidden"
                id="rerank-jd-upload"
              />
              <label htmlFor="rerank-jd-upload" className="cursor-pointer block text-sm">
                <p className="text-gray-700 font-medium">Drag and drop file here</p>
                <p className="text-gray-500 text-xs">or click to browse</p>
              </label>
            </div>
          )}

          {jdFile && <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded">📄 {jdFile.name}</div>}

          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">Top K (Optional)</label>
            <input
              type="number"
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              placeholder="e.g., 10"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-300 rounded-lg p-3 flex gap-2">
              <AlertCircle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700">{error}</p>
            </div>
          )}
        </div>

        <div className="flex gap-2 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleRankAgain}
            disabled={!canSubmit}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Rank Again
          </button>
        </div>
      </div>
    </div>
  )
}
