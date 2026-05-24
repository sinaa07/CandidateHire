"use client"

import { useState } from "react"
import { AlertCircle, CheckCircle2, Loader } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { processCollection, getReport } from "@/utils/api"

export function Phase2Process() {
  const { currentCollection, setProcessingResults, setPhase, setLoading, setError, error, loading } =
    useAppContext()
  const { collection_id, company_id } = currentCollection

  const [isProcessing, setIsProcessing] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [stats, setStats] = useState<{
    total_files: number
    ok: number
    failed: number
    empty: number
    duplicate: number
  } | null>(null)

  const handleStartProcessing = async () => {
    if (!collection_id || !company_id) {
      setError("Missing collection or company ID")
      return
    }

    setLoading(true)
    setIsProcessing(true)
    setError(null)

    try {
      await processCollection(collection_id, company_id)
      const report = await getReport(collection_id, company_id)
      const validationReport = report.phase2?.validation_report
      const statsData = validationReport
        ? {
            total_files: validationReport.total_files || 0,
            ok: validationReport.ok || 0,
            failed: validationReport.failed || 0,
            empty: validationReport.empty || 0,
            duplicate: validationReport.duplicate || 0,
          }
        : { total_files: 0, ok: 0, failed: 0, empty: 0, duplicate: 0 }

      setStats(statsData)
      setProcessingResults(statsData)
      setIsCompleted(true)
      setIsProcessing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process collection")
      setIsProcessing(false)
    } finally {
      setLoading(false)
    }
  }

  const progress = stats && stats.total_files > 0 ? Math.round((stats.ok / stats.total_files) * 100) : 0

  return (
    <div className="px-6 py-10 max-w-2xl mx-auto">
      <header className="mb-8 text-center">
        <h2 className="text-2xl font-bold text-foreground">Processing & Validation</h2>
        <p className="text-muted-foreground mt-1">
          Extract text from resumes and detect duplicates before ranking.
        </p>
        {collection_id && (
          <p className="text-xs font-mono text-muted-foreground mt-3 bg-muted px-3 py-2 rounded-lg inline-block border border-border">
            {collection_id.substring(0, 30)}...
          </p>
        )}
      </header>

      {!isProcessing && !isCompleted && (
        <div className="dashboard-card p-8 text-center">
          <div className="w-20 h-20 bg-muted rounded-2xl flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">⚙️</span>
          </div>
          <p className="text-foreground font-semibold text-lg mb-6">Ready to extract and validate resume data</p>
          <button
            onClick={handleStartProcessing}
            disabled={loading}
            className="px-8 py-3 gradient-primary text-white rounded-lg font-semibold disabled:opacity-50 hover:opacity-90 transition-theme shadow-sm"
          >
            {loading ? "Starting..." : "Start Processing →"}
          </button>
        </div>
      )}

      {isProcessing && (
        <div className="dashboard-card p-8 text-center space-y-6">
          <Loader size={48} className="text-primary animate-spin mx-auto" />
          <div>
            <h3 className="text-lg font-semibold text-foreground">Processing resumes...</h3>
            <p className="text-sm text-muted-foreground mt-1">Extracting text and validating content</p>
          </div>
          <div className="w-full bg-muted h-3 rounded-full overflow-hidden">
            <div
              className="gradient-success h-full rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm font-semibold text-foreground">Progress: {progress}%</p>
        </div>
      )}

      {isCompleted && stats && (
        <div className="space-y-6">
          <div className="flex items-center gap-3 bg-success-50 border border-success-100 text-success p-4 rounded-lg">
            <CheckCircle2 size={24} />
            <span className="font-semibold">Processing Complete</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="dashboard-card p-5">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Total Files</p>
              <p className="text-3xl font-bold text-foreground mt-1">{stats.total_files}</p>
            </div>
            <div className="dashboard-card p-5 border-success/30 bg-success-50">
              <p className="text-xs font-medium text-success uppercase tracking-wide">✓ Processed</p>
              <p className="text-3xl font-bold text-success mt-1">{stats.ok}</p>
            </div>
            <div className="dashboard-card p-5 border-error/30 bg-error-50">
              <p className="text-xs font-medium text-error uppercase tracking-wide">✗ Failed</p>
              <p className="text-3xl font-bold text-error mt-1">{stats.failed}</p>
            </div>
            <div className="dashboard-card p-5 border-warning/30 bg-warning-50">
              <p className="text-xs font-medium text-warning uppercase tracking-wide">≈ Duplicates</p>
              <p className="text-3xl font-bold text-warning mt-1">{stats.duplicate}</p>
            </div>
          </div>

          <button
            onClick={() => setPhase(3)}
            className="btn-primary flex items-center justify-center gap-2"
          >
            Continue to Ranking →
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
