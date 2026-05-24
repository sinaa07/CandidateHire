const STYLES: Record<string, string> = {
  open: "bg-[#ecfdf5] text-[#10B981] border-[#10B981]/30",
  closed: "bg-muted text-muted-foreground border-border",
  draft: "bg-[#fffbeb] text-[#F59E0B] border-[#F59E0B]/30",
  deleted: "bg-muted text-muted-foreground border-border",
  uploaded: "bg-muted text-muted-foreground border-border",
  processing: "bg-[#fffbeb] text-[#F59E0B] border-[#F59E0B]/30",
  processed: "bg-[#ecfdf5] text-[#10B981] border-[#10B981]/30",
  failed: "bg-[#fef2f2] text-[#EF4444] border-[#EF4444]/30",
  duplicate: "bg-orange-50 text-orange-600 border-orange-200",
  indexed: "bg-[#eff6ff] text-[#3B82F6] border-[#3B82F6]/30",
  ranked: "bg-[#eef2ff] text-[#6366F1] border-[#6366F1]/30",
  passed: "bg-[#ecfdf5] text-[#10B981] border-[#10B981]/30",
}

export function StatusBadge({ status }: { status: string }) {
  const key = status.toLowerCase()
  const style = STYLES[key] || "bg-muted text-muted-foreground border-border"
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${style}`}>
      {status}
    </span>
  )
}
