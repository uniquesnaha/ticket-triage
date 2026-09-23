import { useEffect, useState } from 'react'
import { ArrowClockwiseIcon, DownloadSimpleIcon } from '@phosphor-icons/react'
import clsx from 'clsx'
import { api } from './api/client'
import { useTriage } from './hooks/useTriage'
import { exportCSV, exportJSONL } from './lib/export'
import { formatDuration } from './lib/labels'
import type { TriageBatchResponse, TriageResult } from './types/triage'
import { DetailPanel } from './components/DetailPanel'
import { Intake } from './components/Intake'
import { QueueTable, useQueue } from './components/QueueTable'
import { ErrorView, ProcessingView } from './components/StatusViews'
import { Summary } from './components/Summary'
import { TopBar, type HealthState } from './components/TopBar'
import './styles/index.css'

function isTyping(target: EventTarget | null) {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName))
  )
}

function ResultsView({
  fileName,
  response,
  onReset,
}: {
  fileName: string
  response: TriageBatchResponse
  onReset: () => void
}) {
  const { results } = response
  const queue = useQueue(results)
  const [selected, setSelected] = useState<TriageResult | null>(null)
  const index = selected ? queue.visible.indexOf(selected) : -1
  const prev = index > 0 ? queue.visible[index - 1] : null
  const next = index >= 0 && index < queue.visible.length - 1 ? queue.visible[index + 1] : null

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === 'Escape') {
        setSelected(null)
      } else if (e.key === 'j' || e.key === 'ArrowDown') {
        const target = next ?? (selected ? null : queue.visible[0])
        if (!target) return
        setSelected(target)
        e.preventDefault()
      } else if ((e.key === 'k' || e.key === 'ArrowUp') && prev) {
        setSelected(prev)
        e.preventDefault()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, prev, selected, queue.visible])

  return (
    <div className="page page--wide">
      <header className="page-head">
        <div>
          <h1>{fileName}</h1>
          <p className="page-sub">
            {response.total} tickets triaged in {formatDuration(response.processing_time_ms)} with{' '}
            <code>{response.model}</code>
          </p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn btn-quiet" onClick={onReset}>
            <ArrowClockwiseIcon size={15} />
            New file
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => exportCSV(results, fileName)}
          >
            <DownloadSimpleIcon size={15} />
            CSV
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => exportJSONL(results, fileName)}
          >
            <DownloadSimpleIcon size={15} />
            JSONL
          </button>
        </div>
      </header>

      <Summary results={results} />

      <div className={clsx('workspace', selected && 'workspace--split')}>
        <QueueTable results={results} selected={selected} onSelect={setSelected} queue={queue} />
        {selected && (
          <DetailPanel
            result={selected}
            onClose={() => setSelected(null)}
            onPrev={prev ? () => setSelected(prev) : null}
            onNext={next ? () => setSelected(next) : null}
          />
        )}
      </div>
    </div>
  )
}

export default function App() {
  const { state, submit, reset } = useTriage()
  const [health, setHealth] = useState<HealthState>('loading')

  useEffect(() => {
    api.health().then(setHealth, () => setHealth('unreachable'))
  }, [])

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <TopBar health={health} onHome={reset} />
      <main id="main">
        {state.status === 'idle' && <Intake onFile={submit} disabled={false} />}
        {state.status === 'processing' && (
          <ProcessingView
            fileName={state.fileName}
            ticketCount={state.ticketCount}
            startedAt={state.startedAt}
          />
        )}
        {state.status === 'error' && (
          <ErrorView fileName={state.fileName} message={state.message} onRetry={reset} />
        )}
        {state.status === 'success' && (
          <ResultsView fileName={state.fileName} response={state.response} onReset={reset} />
        )}
      </main>
    </>
  )
}
