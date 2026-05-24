"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { setCompanyCredentials } from "@/utils/companyId"

interface CompanyCredentialsSetupProps {
  onSaved: () => void
}

export function CompanyCredentialsSetup({ onSaved }: CompanyCredentialsSetupProps) {
  const [companyId, setCompanyId] = useState("")
  const [apiKey, setApiKey] = useState("")

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    const id = companyId.trim()
    const key = apiKey.trim()
    if (!id || !key) return
    setCompanyCredentials(id, key)
    onSaved()
  }

  return (
    <div className="mx-auto max-w-md rounded-xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-foreground">Connect your company</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Enter the company ID and API key from your CandidateHire database or{" "}
        <code className="rounded bg-muted px-1 text-xs">POST /api/v2/companies</code>.
        Values are saved in this browser only.
      </p>
      <form onSubmit={handleSave} className="mt-6 space-y-4">
        <div>
          <Label htmlFor="setup-company-id">Company ID</Label>
          <Input
            id="setup-company-id"
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            placeholder="e.g. 93aa39dc-cef9-4dfc-9419-589a59a71827"
            className="font-mono text-sm"
            required
          />
        </div>
        <div>
          <Label htmlFor="setup-api-key">API Key</Label>
          <Input
            id="setup-api-key"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="X-Company-API-Key value"
            className="font-mono text-sm"
            required
          />
        </div>
        <Button type="submit" className="w-full gradient-primary text-white">
          Save &amp; continue
        </Button>
      </form>
      <p className="mt-4 text-xs text-muted-foreground">
        Or set{" "}
        <code className="rounded bg-muted px-1">NEXT_PUBLIC_COMPANY_ID</code> and{" "}
        <code className="rounded bg-muted px-1">NEXT_PUBLIC_COMPANY_API_KEY</code> in{" "}
        <code className="rounded bg-muted px-1">frontend/.env.local</code> and restart the dev
        server.
      </p>
    </div>
  )
}
