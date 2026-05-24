"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { createJob } from "@/utils/api.v2"

interface CreateJobModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  onSuccess: () => void
}

export function CreateJobModal({ open, onOpenChange, companyId, onSuccess }: CreateJobModalProps) {
  const [title, setTitle] = useState("")
  const [department, setDepartment] = useState("")
  const [status, setStatus] = useState("open")
  const [jdText, setJdText] = useState("")
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      setError("Title is required")
      return
    }
    if (!jdText.trim() && !jdFile) {
      setError("Provide JD text or upload a JD file")
      return
    }

    setLoading(true)
    setError(null)
    try {
      await createJob(companyId, {
        title: title.trim(),
        department: department.trim() || undefined,
        status,
        jd_text: jdText.trim() || undefined,
        jd_file: jdFile,
      })
      setTitle("")
      setDepartment("")
      setStatus("open")
      setJdText("")
      setJdFile(null)
      onSuccess()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create New Job</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="title">Job Title</Label>
            <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="department">Department</Label>
            <Input id="department" value={department} onChange={(e) => setDepartment(e.target.value)} />
          </div>
          <div>
            <Label>Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="jd_text">JD Text</Label>
            <Textarea
              id="jd_text"
              rows={5}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste job description..."
            />
          </div>
          <div>
            <Label htmlFor="jd_file">JD File (optional)</Label>
            <Input
              id="jd_file"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setJdFile(e.target.files?.[0] ?? null)}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} className="gradient-primary text-white">
              {loading ? "Creating..." : "Create Job"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
