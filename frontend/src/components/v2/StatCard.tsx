interface StatCardProps {
  label: string
  value: number | string
  borderColor: string
}

export function StatCard({ label, value, borderColor }: StatCardProps) {
  return (
    <div
      className="rounded-xl border border-border bg-card p-5 shadow-sm"
      style={{ borderLeftWidth: 4, borderLeftColor: borderColor }}
    >
      <p className="text-3xl font-bold text-foreground">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{label}</p>
    </div>
  )
}
