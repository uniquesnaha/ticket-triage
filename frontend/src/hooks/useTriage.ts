import { useState, useCallback } from 'react'
import { triageAPI } from '../api/client'
import type { TriageBatchResponse } from '../types/triage'

export type TriageStatus = 'idle' | 'processing' | 'success' | 'error'

export interface UseTriageReturn {
  status: TriageStatus
  response: TriageBatchResponse | null
  error: string | null
  uploadCSV: (file: File) => Promise<void>
  reset: () => void
}

export function useTriage(): UseTriageReturn {
  const [status, setStatus] = useState<TriageStatus>('idle')
  const [response, setResponse] = useState<TriageBatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const uploadCSV = useCallback(async (file: File) => {
    setStatus('processing')
    setError(null)
    setResponse(null)
    try {
      const result = await triageAPI.triageCSV(file)
      setResponse(result)
      setStatus('success')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
      setStatus('error')
    }
  }, [])

  const reset = useCallback(() => {
    setStatus('idle')
    setResponse(null)
    setError(null)
  }, [])

  return { status, response, error, uploadCSV, reset }
}
