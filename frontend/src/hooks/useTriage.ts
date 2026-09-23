import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { TriageBatchResponse } from '../types/triage'

export type TriageState =
  | { status: 'idle' }
  | { status: 'processing'; fileName: string; ticketCount: number | null; startedAt: number }
  | { status: 'success'; fileName: string; response: TriageBatchResponse }
  | { status: 'error'; fileName: string; message: string }

/** Rough row count for the loading message; quoted multi-line cells are rare in exports. */
async function countRows(file: File): Promise<number | null> {
  try {
    const lines = (await file.text()).split(/\r?\n/).filter((l) => l.trim() !== '')
    return Math.max(lines.length - 1, 0)
  } catch {
    return null
  }
}

export function useTriage() {
  const [state, setState] = useState<TriageState>({ status: 'idle' })
  const runId = useRef(0)

  const submit = useCallback(async (file: File) => {
    const id = ++runId.current
    setState({ status: 'processing', fileName: file.name, ticketCount: null, startedAt: Date.now() })
    countRows(file).then((ticketCount) => {
      if (runId.current === id) {
        setState((s) => (s.status === 'processing' ? { ...s, ticketCount } : s))
      }
    })
    try {
      const response = await api.triageCSV(file)
      if (runId.current === id) setState({ status: 'success', fileName: file.name, response })
    } catch (error) {
      if (runId.current === id) {
        const message = error instanceof Error ? error.message : 'Something went wrong. Try again.'
        setState({ status: 'error', fileName: file.name, message })
      }
    }
  }, [])

  const reset = useCallback(() => {
    runId.current++
    setState({ status: 'idle' })
  }, [])

  return { state, submit, reset }
}

export function useElapsedSeconds(since: number | null): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (since === null) return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [since])
  return since === null ? 0 : Math.max(0, Math.floor((now - since) / 1000))
}
