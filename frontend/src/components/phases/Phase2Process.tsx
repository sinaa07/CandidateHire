"use client"

import { useState } from "react"
import { AlertCircle, CheckCircle2, Loader } from "lucide-react"
import { useAppContext } from "@/contexts/AppContext"
import { processCollection, getReport } from "@/utils/api"

export function Phase2Process() {
  const { currentCollection, setProcessingResults, setPhase, setLoading, setError, error, loading } = useAppContext()
  const { collection_id, company_id } = currentCollection

  const [isProcessing, setIsProcessing] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [stats, setStats] = useState<any>(null)

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

      // Fetch report to get stats
      const report = await getReport(collection_id, company_id)
      // validation_report has stats at the top level (spread from stats object)
      const validationReport = report.phase2.validation_report
      const statsData = validationReport ? {
        total_files: validationReport.total_files || 0,
        ok: validationReport.ok || 0,
        failed: validationReport.failed || 0,
        empty: validationReport.empty || 0,
        duplicate: validationReport.duplicate || 0,
      } : {
        total_files: 0,
        ok: 0,
        failed: 0,
        empty: 0,
        duplicate: 0,
      }

      setStats(statsData)
      setProcessingResults(statsData)
      setIsCompleted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process collection")
      setIsProcessing(false)
    } finally {
      setLoading(false)
    }
  }

  const progress = stats ? Math.round((stats.ok / stats.total_files) * 100) : 0

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="mb-8">
        <h2 className="text-4xl font-bold text-[#262626] mb-2">Processing Resumes</h2>
        <p className="text-[#737373]">Extract and validate resume data from your collection</p>
      </div>

      <div className="space-y-6">
        {currentCollection.collection_id && (
          <div className="text-sm text-[#737373] bg-white border border-[#E5E5E5] p-3 rounded-lg font-mono">
            Collection ID: {currentCollection.collection_id.substring(0, 30)}...
          </div>
        )}

        {!isProcessing && !isCompleted && (
          <div className="bg-white border border-[#E5E5E5] rounded-lg p-8 shadow-card text-center">
            <div className="w-16 h-16 bg-[#F5F5F5] rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">⚙️</span>
            </div>
            <p className="text-[#262626] font-medium mb-6">Ready to extract and validate resume data</p>
            <button
              onClick={handleStartProcessing}
              disabled={loading}
              className="px-6 py-3 gradient-primary text-white rounded-lg font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-card"
            >
              {loading ? "Starting..." : "Start Processing →"}
            </button>
          </div>
        )}

        {isProcessing && (
          <div className="bg-white border border-[#E5E5E5] rounded-lg p-8 shadow-card">
            <div className="text-center mb-6">
              <Loader size={48} className="mx-auto text-[#6366F1] animate-spin mb-4" />
              <p className="text-[#262626] font-semibold text-lg mb-2">Processing resumes...</p>
              <p className="text-[#737373] text-sm">Extracting text and validating content</p>
            </div>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm text-[#737373] mb-2">
                  <span>Progress</span>
                  <span className="font-semibold text-[#262626]">{progress}%</span>
                </div>
                <div className="w-full bg-[#F5F5F5] rounded-full h-3 overflow-hidden">
                  <div
                    className="gradient-success h-full transition-all duration-500 ease-out rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
              {stats && (
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[#E5E5E5]">
                  <div>
                    <p className="text-xs text-[#737373] mb-1">Processed</p>
                    <p className="text-2xl font-bold text-[#10B981]">{stats.ok}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#737373] mb-1">Total</p>
                    <p className="text-2xl font-bold text-[#262626]">{stats.total_files}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {isCompleted && stats && (
          <>
            <div className="flex items-center gap-3 text-[#10B981] bg-[#ECFDF5] border border-[#10B981] p-4 rounded-lg">
              <CheckCircle2 size={24} />
              <span className="font-semibold">Processing Complete</span>
            </div>

            <div className="bg-white border border-[#E5E5E5] rounded-lg p-6 shadow-card">
              <h3 className="font-semibold text-[#262626] mb-6 text-lg">Processing Summary</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#F5F5F5] rounded-lg p-4">
                  <p className="text-sm text-[#737373] mb-1">Total Files</p>
                  <p className="text-2xl font-bold text-[#262626]">{stats.total_files}</p>
                </div>
                <div className="bg-[#ECFDF5] rounded-lg p-4 border border-[#10B981]">
                  <p className="text-sm text-[#10B981] mb-1">✓ Successfully Processed</p>
                  <p className="text-2xl font-bold text-[#10B981]">{stats.ok}</p>
                </div>
                <div className="bg-[#FEE2E2] rounded-lg p-4 border border-[#EF4444]">
                  <p className="text-sm text-[#EF4444] mb-1">✗ Failed</p>
                  <p className="text-2xl font-bold text-[#EF4444]">{stats.failed}</p>
                </div>
                <div className="bg-[#FEF3C7] rounded-lg p-4 border border-[#F59E0B]">
                  <p className="text-sm text-[#F59E0B] mb-1">≈ Duplicates</p>
                  <p className="text-2xl font-bold text-[#F59E0B]">{stats.duplicate}</p>
                </div>
              </div>
            </div>

            <button
              onClick={() => setPhase(3)}
              className="w-full gradient-primary text-white py-4 rounded-lg font-semibold hover:opacity-90 transition-all shadow-card hover:shadow-lg hover:-translate-y-0.5 flex items-center justify-center gap-2"
            >
              Continue to Ranking
              <span>→</span>
            </button>
          </>
        )}

        {error && (
          <div className="bg-[#FEE2E2] border border-[#EF4444] rounded-lg p-4 flex gap-3">
            <AlertCircle size={20} className="text-[#EF4444] flex-shrink-0" />
            <p className="text-sm text-[#DC2626]">{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
