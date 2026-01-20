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
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="mb-8">
        <h2 className="text-4xl font-bold text-[#262626] mb-2">Rank Candidates</h2>
        <p className="text-[#737373]">Match resumes against job description</p>
      </div>

      {!isCompleted && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Job Description Section */}
          <div className="bg-white border border-[#E5E5E5] rounded-lg p-6 shadow-card">
            <h3 className="font-semibold text-[#262626] mb-4">Job Description</h3>
            <div className="flex gap-2 bg-[#F5F5F5] p-1 rounded-lg mb-4">
              <button
                onClick={() => setMode("text")}
                className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  mode === "text"
                    ? "bg-white text-[#6366F1] shadow-sm"
                    : "text-[#737373] hover:text-[#262626]"
                }`}
              >
                Paste Text
              </button>
              <button
                onClick={() => setMode("file")}
                className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  mode === "file"
                    ? "bg-white text-[#6366F1] shadow-sm"
                    : "text-[#737373] hover:text-[#262626]"
                }`}
              >
                Upload File
              </button>
            </div>

            {mode === "text" && (
              <textarea
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value)
                  setError(null)
                }}
                placeholder="Enter or paste the job description here..."
                className="w-full px-4 py-3 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6366F1] focus:border-transparent min-h-64 resize-vertical bg-white"
              />
            )}

            {mode === "file" && (
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
                  dragActive ? "border-[#6366F1] bg-[#EEF2FF]" : "border-[#E5E5E5] hover:border-[#6366F1] bg-[#F5F5F5]"
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
                  <UploadIcon size={32} className={`mx-auto mb-2 ${dragActive ? "text-[#6366F1]" : "text-[#737373]"}`} />
                  <p className="text-[#262626] font-medium">Drop JD.pdf or Browse</p>
                  <p className="text-[#737373] text-sm mt-1">Supported: .pdf, .docx, .txt</p>
                </label>
              </div>
            )}

            {jdFile && (
              <div className="mt-4 bg-[#F5F5F5] border border-[#E5E5E5] rounded-lg p-3">
                <p className="text-sm text-[#262626] font-medium">📄 {jdFile.name}</p>
              </div>
            )}
          </div>

          {/* Ranking Config Section */}
          <div className="bg-white border border-[#E5E5E5] rounded-lg p-6 shadow-card">
            <h3 className="font-semibold text-[#262626] mb-4">Ranking Config</h3>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-[#262626] mb-2">Top Candidates</label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  placeholder="e.g., 10"
                  className="w-full px-4 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6366F1] focus:border-transparent bg-white"
                />
                <p className="text-xs text-[#737373] mt-1">Leave empty to rank all candidates</p>
              </div>

              <div>
                <p className="text-sm font-medium text-[#262626] mb-3">Algorithm</p>
                <div className="space-y-2">
                  <label className="flex items-center gap-3 p-3 bg-[#F5F5F5] rounded-lg cursor-pointer hover:bg-[#EEF2FF] transition-colors">
                    <input type="radio" name="algorithm" defaultChecked className="text-[#6366F1]" />
                    <span className="text-sm text-[#262626]">Semantic Match</span>
                  </label>
                </div>
              </div>

              <div className="pt-4 border-t border-[#E5E5E5]">
                <p className="text-sm text-[#737373] mb-2">⏱️ Estimated time: ~30 sec</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6 bg-[#FEE2E2] border border-[#EF4444] rounded-lg p-4 flex gap-3">
          <AlertCircle size={20} className="text-[#EF4444] flex-shrink-0" />
          <p className="text-sm text-[#DC2626]">{error}</p>
        </div>
      )}

      {!isCompleted && (
        <div className="mt-6">
          <button
            onClick={handleRank}
            disabled={!canSubmit || loading}
            className="w-full gradient-primary text-white py-4 rounded-lg font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-card hover:shadow-lg hover:-translate-y-0.5 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader size={20} className="animate-spin" />
                Ranking...
              </>
            ) : (
              "Start Ranking →"
            )}
          </button>
        </div>
      )}

      {isCompleted && (
        <div className="space-y-6">
          <div className="flex items-center gap-3 text-[#10B981] bg-[#ECFDF5] border border-[#10B981] p-4 rounded-lg">
            <CheckCircle2 size={24} />
            <span className="font-semibold">Ranking Complete - {rankingCount} candidates ranked</span>
          </div>

          <button
            onClick={() => setPhase(4)}
            className="w-full gradient-primary text-white py-4 rounded-lg font-semibold hover:opacity-90 transition-all shadow-card hover:shadow-lg hover:-translate-y-0.5 flex items-center justify-center gap-2"
          >
            View Results
            <span>→</span>
          </button>
        </div>
      )}
    </div>
  )
}
