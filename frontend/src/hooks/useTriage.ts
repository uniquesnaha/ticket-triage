import { useState, useCallback } from 'react'
import { ApiError, accessKey, triageAPI } from '../api/client'
import type { TriageBatchResponse } from '../types/triage'

export type TriageStatus = 'idle' | 'processing' | 'success' | 'error'

export interface UseTriageReturn {
  status: TriageStatus
  response: TriageBatchResponse | null
  error: string | null
  uploadCSV: (file: File) => Promise<void>
  reset: () => void
}

export function useTriage(onUnauthorized: () => void): UseTriageReturn {
  const [status, setStatus] = useState<TriageStatus>('idle')
  const [response, setResponse] = useState<TriageBatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const uploadCSV = useCallback(
    async (file: File) => {
      setStatus('processing')
      setError(null)
      setResponse(null)
      try {
        setResponse(await triageAPI.triageCSV(file))
        setStatus('success')
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          accessKey.clear()
          onUnauthorized()
          setError('The access key was rejected. Please enter a valid key.')
        } else {
          setError(err instanceof Error ? err.message : 'Unknown error occurred')
        }
        setStatus('error')
      }
    },
    [onUnauthorized],
  )

  const reset = useCallback(() => {
    setStatus('idle')
    setResponse(null)
    setError(null)
  }, [])

  return { status, response, error, uploadCSV, reset }
}
