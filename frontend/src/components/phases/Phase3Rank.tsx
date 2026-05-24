"use client"

import type React from "react"
import { useState } from "react"
import { AlertCircle, CheckCircle2, UploadIcon, Loader } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { rankCollectionText, rankCollectionFile } from "@/utils/api"

export function Phase3Rank() {
  const { currentCollection, setRankingResults, setPhase, setLoading, setError, error, loading } =
    useAppContext()
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
      const response =
        mode === "text"
          ? await rankCollectionText(collection_id, company_id, jdText, topKNum)
          : await rankCollectionFile(collection_id, company_id, jdFile!, topKNum)

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
    if (file.name.match(/\.(pdf|docx|txt)$/i)) {
      setJdFile(file)
      setError(null)
    } else {
      setError("Please select a valid file (.pdf, .docx, .txt)")
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(e.type === "dragenter" || e.type === "dragover")
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) handleFileSelect(e.dataTransfer.files[0])
  }

  return (
    <div className="px-6 py-10">
      <header className="mb-8">
        <h2 className="text-2xl font-bold text-foreground">Semantic Ranking</h2>
        <p className="text-muted-foreground mt-1">
          Provide a job description to rank candidates by fit.
        </p>
      </header>

      {!isCompleted ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="dashboard-card p-6">
            <h3 className="font-semibold text-foreground mb-4">Job Description</h3>
            <div className="flex gap-1 bg-muted p-1 rounded-lg mb-4">
              <button
                onClick={() => setMode("text")}
                className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-theme ${
                  mode === "text" ? "bg-card text-primary shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Paste Text
              </button>
              <button
                onClick={() => setMode("file")}
                className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-theme ${
                  mode === "file" ? "bg-card text-primary shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Upload File
              </button>
            </div>

            {mode === "text" ? (
              <textarea
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value)
                  setError(null)
                }}
                placeholder="Enter or paste the job description here..."
                className="dashboard-input min-h-64 resize-y"
              />
            ) : (
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-12 text-center transition-theme ${
                  dragActive ? "border-primary bg-primary-50" : "border-border hover:border-primary hover:bg-primary-50/50"
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
                  <UploadIcon size={32} className="mx-auto text-primary mb-3" />
                  <p className="font-semibold text-foreground">Drop JD file or Browse</p>
                  <p className="text-sm text-muted-foreground mt-1">Supported: .pdf, .docx, .txt</p>
                </label>
              </div>
            )}

            {jdFile && (
              <p className="mt-3 text-sm text-foreground bg-success-50 border border-success-100 rounded-lg px-3 py-2">
                📄 {jdFile.name}
              </p>
            )}
          </div>

          <div className="dashboard-card p-6">
            <h3 className="font-semibold text-foreground mb-4">Ranking Configuration</h3>
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Top Candidates</label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  placeholder="e.g., 10"
                  className="dashboard-input"
                />
                <p className="text-xs text-muted-foreground mt-1.5">Leave empty to rank all candidates</p>
              </div>

              <div>
                <p className="text-sm font-medium text-foreground mb-2">Algorithm</p>
                <label className="flex items-center gap-3 p-3 bg-muted rounded-lg cursor-pointer hover:bg-primary-50 transition-theme">
                  <input type="radio" name="algorithm" defaultChecked className="accent-primary" />
                  <span className="text-sm font-medium text-foreground">Semantic Match</span>
                </label>
              </div>

              <p className="text-sm text-muted-foreground flex items-center gap-2 pt-2 border-t border-border">
                <span>⏱️</span> Estimated time: ~30 sec
              </p>
            </div>

            <button
              onClick={handleRank}
              disabled={!canSubmit || loading}
              className="btn-primary mt-6 flex items-center justify-center gap-2"
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
        </div>
      ) : (
        <div className="space-y-6 max-w-2xl">
          <div className="flex items-center gap-3 bg-success-50 border border-success-100 text-success p-5 rounded-xl">
            <CheckCircle2 size={24} />
            <span className="font-semibold">Ranking Complete — {rankingCount} candidates ranked</span>
          </div>
          <button onClick={() => setPhase(4)} className="btn-primary flex items-center justify-center gap-2">
            View Results →
          </button>
        </div>
      )}

      {error && (
        <div className="mt-6 bg-error-50 border border-error-100 rounded-lg p-4 flex gap-3">
          <AlertCircle size={20} className="text-error shrink-0" />
          <p className="text-sm text-error font-medium">{error}</p>
        </div>
      )}
    </div>
  )
}
