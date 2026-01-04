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
      const statsData = report.phase2.validation_report?.stats || {
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

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <h2 className="text-3xl font-bold text-gray-900 mb-2">Phase 2: Process Resumes</h2>
      <p className="text-gray-600 mb-8">Extract and validate resume data from your collection.</p>

      <div className="space-y-6">
        {currentCollection.collection_id && (
          <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg">
            Collection ID: {currentCollection.collection_id.substring(0, 30)}...
          </div>
        )}

        {!isProcessing && !isCompleted && (
          <>
            <p className="text-gray-700">Ready to extract and validate resume data.</p>
            <button
              onClick={handleStartProcessing}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Starting..." : "Start Processing"}
            </button>
          </>
        )}

        {isProcessing && (
          <div className="text-center py-8 space-y-4">
            <Loader size={40} className="mx-auto text-blue-600 animate-spin" />
            <p className="text-gray-700 font-medium">Processing resumes...</p>
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div className="bg-blue-600 h-full animate-pulse" style={{ width: "67%" }} />
            </div>
          </div>
        )}

        {isCompleted && stats && (
          <>
            <div className="flex items-center gap-2 text-green-700 bg-green-50 p-4 rounded-lg border border-green-200">
              <CheckCircle2 size={24} />
              <span className="font-medium">Processing Complete</span>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Processing Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-gray-700">
                  <span>Total Files:</span>
                  <span className="font-medium">{stats.total_files}</span>
                </div>
                <div className="flex justify-between text-green-700">
                  <span>✓ Successfully Processed:</span>
                  <span className="font-medium">{stats.ok}</span>
                </div>
                <div className="flex justify-between text-red-700">
                  <span>✗ Failed:</span>
                  <span className="font-medium">{stats.failed}</span>
                </div>
                <div className="flex justify-between text-gray-700">
                  <span>○ Empty:</span>
                  <span className="font-medium">{stats.empty}</span>
                </div>
                <div className="flex justify-between text-yellow-700">
                  <span>≈ Duplicates:</span>
                  <span className="font-medium">{stats.duplicate}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setPhase(3)}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              Continue to Ranking
              <span>→</span>
            </button>
          </>
        )}

        {error && (
          <div className="bg-red-50 border border-red-300 rounded-lg p-4 flex gap-3">
            <AlertCircle size={20} className="text-red-600 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
