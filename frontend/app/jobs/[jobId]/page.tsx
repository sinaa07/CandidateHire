"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { format } from "date-fns"
import { Upload } from "lucide-react"
import { V2Nav } from "@/components/v2/V2Nav"
import { StatusBadge } from "@/components/v2/StatusBadge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  getJob,
  getPipelineStatus,
  getResumes,
  triggerIndex,
  triggerRank,
  updateJob,
  uploadResumes,
} from "@/utils/api.v2"
import { getCompanyId } from "@/utils/companyId"
import type { JobRead, PipelineStatus, ResumeListItem } from "@/types/v2"

export default function JobDetailPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.jobId as string
  const companyId = getCompanyId()

  const [job, setJob] = useState<JobRead | null>(null)
  const [resumes, setResumes] = useState<ResumeListItem[]>([])
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [jdExpanded, setJdExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const [editDept, setEditDept] = useState("")
  const [editStatus, setEditStatus] = useState("open")
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string | null>(null)
  const [indexing, setIndexing] = useState(false)
  const [ranking, setRanking] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    if (!companyId || !jobId) return
    setLoading(true)
    setError(null)
    try {
      const [jobData, resumeList, status] = await Promise.all([
        getJob(companyId, jobId),
        getResumes(companyId, jobId),
        getPipelineStatus(companyId, jobId),
      ])
      setJob(jobData)
      setResumes(resumeList)
      setPipeline(status)
      setEditTitle(jobData.title)
      setEditDept(jobData.department || "")
      setEditStatus(jobData.status)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load job")
    } finally {
      setLoading(false)
    }
  }, [companyId, jobId])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!indexing || !companyId || !jobId) return
    const interval = setInterval(async () => {
      try {
        const status = await getPipelineStatus(companyId, jobId)
        setPipeline(status)
        if (status.indexing_complete) {
          setIndexing(false)
          await load()
        }
      } catch {
        /* ignore poll errors */
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [indexing, companyId, jobId, load])

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length || !companyId) return
    setUploading(true)
    setUploadProgress(`Uploading ${files.length} file(s)...`)
    try {
      const list = Array.from(files)
      const zip = list.find((f) => f.name.endsWith(".zip"))
      const others = list.filter((f) => !f.name.endsWith(".zip"))
      await uploadResumes(companyId, jobId, others, zip || null)
      setUploadProgress("Upload complete")
      await load()
    } catch (err) {
      setUploadProgress(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
      setTimeout(() => setUploadProgress(null), 3000)
    }
  }

  const handleIndex = async () => {
    if (!companyId) return
    setIndexing(true)
    try {
      await triggerIndex(companyId, jobId)
      const status = await getPipelineStatus(companyId, jobId)
      setPipeline(status)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Indexing failed")
      setIndexing(false)
    }
  }

  const handleRank = async () => {
    if (!companyId) return
    setRanking(true)
    try {
      await triggerRank(companyId, jobId)
      router.push(`/jobs/${jobId}/rankings`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ranking failed")
    } finally {
      setRanking(false)
    }
  }

  const saveEdits = async () => {
    if (!companyId || !job) return
    try {
      const updated = await updateJob(companyId, jobId, {
        title: editTitle,
        department: editDept || undefined,
        status: editStatus,
      })
      setJob(updated)
      setEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed")
    }
  }

  const jdPreview = job?.jd_text
    ? jdExpanded
      ? job.jd_text
      : job.jd_text.slice(0, 300) + (job.jd_text.length > 300 ? "..." : "")
    : ""

  const processedCount = pipeline ? pipeline.processed + pipeline.failed + pipeline.duplicate : 0

  return (
    <div className="min-h-screen bg-background">
      <V2Nav />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6">
          <Link href="/" className="text-sm text-primary hover:underline">
            ← Back to Dashboard
          </Link>
        </div>

        {loading && <p className="text-muted-foreground">Loading job...</p>}
        {error && (
          <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {job && (
          <div className="space-y-8">
            <section className="rounded-xl border border-border bg-card p-6 shadow-sm">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                <div>
                  {editing ? (
                    <div className="space-y-3 max-w-md">
                      <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                      <Input
                        value={editDept}
                        placeholder="Department"
                        onChange={(e) => setEditDept(e.target.value)}
                      />
                      <Select value={editStatus} onValueChange={setEditStatus}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="open">Open</SelectItem>
                          <SelectItem value="draft">Draft</SelectItem>
                          <SelectItem value="closed">Closed</SelectItem>
                        </SelectContent>
                      </Select>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={saveEdits}>
                          Save
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <h1 className="text-2xl font-bold text-foreground">{job.title}</h1>
                      {job.department && (
                        <p className="text-sm text-muted-foreground">{job.department}</p>
                      )}
                      <div className="mt-2 flex flex-wrap gap-2">
                        <StatusBadge status={job.status} />
                        <StatusBadge status={job.pipeline_stage} />
                      </div>
                      <p className="mt-2 text-xs text-muted-foreground">
                        Created {format(new Date(job.created_at), "MMM d, yyyy")}
                      </p>
                    </>
                  )}
                </div>
                {!editing && (
                  <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                    Edit
                  </Button>
                )}
              </div>

              {job.jd_text && (
                <div className="mt-4">
                  <Label className="text-muted-foreground">Job Description</Label>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">{jdPreview}</p>
                  {job.jd_text.length > 300 && (
                    <button
                      type="button"
                      className="mt-2 text-sm text-primary hover:underline"
                      onClick={() => setJdExpanded(!jdExpanded)}
                    >
                      {jdExpanded ? "Show less" : "Show more"}
                    </button>
                  )}
                </div>
              )}
            </section>

            <section className="rounded-xl border border-border bg-card p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold">Resumes</h2>

              <div
                className="mb-6 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border bg-muted/30 p-10 transition-colors hover:border-primary/50 hover:bg-muted/50"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault()
                  handleFiles(e.dataTransfer.files)
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium text-foreground">
                  Drag & drop resumes or click to browse
                </p>
                <p className="mt-1 text-xs text-muted-foreground">PDF, DOCX, TXT, or ZIP</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.zip"
                  className="hidden"
                  onChange={(e) => handleFiles(e.target.files)}
                />
              </div>

              {uploadProgress && (
                <p className="mb-4 text-sm text-muted-foreground">{uploadProgress}</p>
              )}
              {uploading && (
                <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full w-1/2 animate-pulse bg-primary" />
                </div>
              )}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Uploaded</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resumes.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium">{r.filename}</TableCell>
                      <TableCell>
                        <StatusBadge status={r.status} />
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {format(new Date(r.created_at), "MMM d, yyyy HH:mm")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {resumes.length === 0 && (
                <p className="py-6 text-center text-sm text-muted-foreground">No resumes uploaded yet.</p>
              )}

              <div className="mt-6 flex flex-wrap items-center gap-4 rounded-lg border border-border bg-muted/20 p-4">
                <Button
                  onClick={handleIndex}
                  disabled={indexing || resumes.length === 0}
                  variant="outline"
                >
                  {indexing ? "Indexing..." : "Index Resumes"}
                </Button>
                {pipeline && indexing && (
                  <span className="text-sm text-muted-foreground">
                    Indexing: {processedCount} / {pipeline.total} processed
                  </span>
                )}
                {pipeline && !indexing && (
                  <span className="text-sm text-muted-foreground">
                    {pipeline.processed} processed · {pipeline.uploaded} queued
                  </span>
                )}
                <Button
                  onClick={handleRank}
                  disabled={!pipeline?.indexing_complete || ranking}
                  className="gradient-primary text-white"
                >
                  {ranking ? "Ranking..." : "Rank Candidates"}
                </Button>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
