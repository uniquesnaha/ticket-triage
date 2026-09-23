import { useCallback, useRef, useState } from 'react'
import { api } from '../api/client'
import type { TriageResult } from '../types/triage'

export function useSingleTicket() {
  const [history, setHistory] = useState<TriageResult[]>([])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const counter = useRef(0)

  const classify = useCallback(async (text: string) => {
    const ticketId = `MANUAL-${++counter.current}`
    setPending(true)
    setError(null)
    try {
      const response = await api.triageTickets([{ ticket_id: ticketId, text }])
      setHistory((h) => [response.results[0], ...h])
      return true
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Try again.')
      return false
    } finally {
      setPending(false)
    }
  }, [])

  return { history, pending, error, classify }
}
