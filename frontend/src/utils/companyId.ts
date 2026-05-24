const COMPANY_ID_KEY = "candidatehire_company_id"
const API_KEY_KEY = "candidatehire_api_key"

export function getCompanyId(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(COMPANY_ID_KEY)
    if (stored) return stored
  }
  return process.env.NEXT_PUBLIC_COMPANY_ID || ""
}

export function getApiKey(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(API_KEY_KEY)
    if (stored) return stored
  }
  return process.env.NEXT_PUBLIC_COMPANY_API_KEY || ""
}

export function setCompanyCredentials(companyId: string, apiKey: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(COMPANY_ID_KEY, companyId)
    localStorage.setItem(API_KEY_KEY, apiKey)
  }
}

export function setCompanyId(companyId: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(COMPANY_ID_KEY, companyId)
  }
}
