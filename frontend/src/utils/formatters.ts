export function formatScore(score: number): string {
  return `${(score * 100).toFixed(2)}%`
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i]
}

export function getScoreBgColor(score: number): string {
  const percentage = score * 100
  if (percentage >= 80) return "bg-green-100"
  if (percentage >= 60) return "bg-yellow-100"
  return "bg-red-100"
}

export function getScoreTextColor(score: number): string {
  const percentage = score * 100
  if (percentage >= 80) return "text-green-700"
  if (percentage >= 60) return "text-yellow-700"
  return "text-red-700"
}

export function truncateFilename(filename: string, maxLength = 30): string {
  if (filename.length <= maxLength) return filename
  return filename.substring(0, maxLength) + "..."
}
