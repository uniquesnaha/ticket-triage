import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { saveRun } from '../lib/store'
import type { HealthResponse } from '../types/triage'

export type HealthState = HealthResponse | 'loading' | 'unreachable'

/** The CSV batch currently being processed (at most one at a time). */
export type Job =
  | { status: 'processing'; fileName: string; ticketCount: number | null; startedAt: number }
  | { status: 'error'; fileName: string; message: string }

interface TriageContextValue {
  health: HealthState
  job: Job | null
  submitFile: (file: File) => void
  clearJob: () => void
}

const TriageContext = createContext<TriageContextValue | null>(null)

/** Rough row count for the loading message; quoted multi-line cells are rare in exports. */
async function countRows(file: File): Promise<number | null> {
  try {
    const lines = (await file.text()).split(/\r?\n/).filter((l) => l.trim() !== '')
    return Math.max(lines.length - 1, 0)
  } catch {
    return null
  }
}

export function TriageProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [health, setHealth] = useState<HealthState>('loading')
  const [job, setJob] = useState<Job | null>(null)
  const jobId = useRef(0)

  useEffect(() => {
    api.health().then(setHealth, () => setHealth('unreachable'))
  }, [])

  const submitFile = useCallback(
    async (file: File) => {
      const id = ++jobId.current
      setJob({ status: 'processing', fileName: file.name, ticketCount: null, startedAt: Date.now() })
      navigate('/')
      countRows(file).then((ticketCount) => {
        if (jobId.current === id) {
          setJob((j) => (j?.status === 'processing' ? { ...j, ticketCount } : j))
        }
      })
      try {
        const response = await api.triageCSV(file)
        if (jobId.current !== id) return
        const run = saveRun(file.name, response)
        setJob(null)
        navigate(`/runs/${run.id}`)
      } catch (error) {
        if (jobId.current !== id) return
        const message = error instanceof Error ? error.message : 'Something went wrong. Try again.'
        setJob({ status: 'error', fileName: file.name, message })
      }
    },
    [navigate],
  )

  const clearJob = useCallback(() => {
    jobId.current++
    setJob(null)
  }, [])

  return (
    <TriageContext.Provider value={{ health, job, submitFile, clearJob }}>
      {children}
    </TriageContext.Provider>
  )
}

export function useTriageApp(): TriageContextValue {
  const value = useContext(TriageContext)
  if (!value) throw new Error('useTriageApp must be used inside TriageProvider')
  return value
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
