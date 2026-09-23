import type { HealthResponse, RuleInfo, TriageBatchResponse } from '../types/triage'

// Same-origin API: a Vercel rewrite in production, the Vite proxy in development.

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface ProblemDetails {
  detail?: string | { msg: string }[]
}

function messageFor(status: number, body: ProblemDetails | null): string {
  switch (status) {
    case 413:
      return 'The file is too large. The limit is 4 MB.'
    case 429:
      return 'Too many requests from this address. Wait a minute and try again.'
    case 502:
    case 504:
      return 'The server took too long to respond. Try again with fewer tickets.'
  }
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return `The server returned an error (${status}). Try again.`
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 90_000): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(path, { ...init, signal: controller.signal })
    const body = (await response.json().catch(() => null)) as unknown
    if (!response.ok) throw new ApiError(messageFor(response.status, body as ProblemDetails | null), response.status)
    return body as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The request timed out. Try again with fewer tickets.', null)
    }
    throw new ApiError('Could not reach the server. Check your connection and try again.', null)
  } finally {
    window.clearTimeout(timer)
  }
}

export const api = {
  health: () => request<HealthResponse>('/api/v1/health', {}, 10_000),

  rules: () => request<RuleInfo[]>('/api/v1/rules', {}, 10_000),

  triageTickets: (tickets: { ticket_id: string; text: string }[]) =>
    request<TriageBatchResponse>('/api/v1/triage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickets }),
    }),

  triageCSV: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<TriageBatchResponse>('/api/v1/triage/upload', { method: 'POST', body: form })
  },
}
