"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

export function V2Nav() {
  const pathname = usePathname()
  const isHome = pathname === "/"
  const isJobs = pathname.startsWith("/jobs")

  return (
    <nav className="sticky top-0 z-40 border-b border-border bg-card shadow-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-primary text-sm font-bold text-white">
              C
            </div>
            <span className="text-base font-bold text-foreground">CandidateHire</span>
          </Link>
          <div className="hidden items-center gap-1 sm:flex">
            <Link
              href="/"
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isHome ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"
              }`}
            >
              Dashboard
            </Link>
            {isJobs && (
              <span className="rounded-lg bg-primary/10 px-3 py-2 text-sm font-medium text-primary">
                Job
              </span>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
