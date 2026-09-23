import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { DownloadSimpleIcon, TrashIcon } from '@phosphor-icons/react'
import clsx from 'clsx'
import { DetailPanel } from '../components/DetailPanel'
import { QueueTable, useQueue } from '../components/QueueTable'
import { Summary } from '../components/Summary'
import { exportCSV, exportJSONL } from '../lib/export'
import { formatDuration } from '../lib/labels'
import { deleteRun, formatRelative, useRuns, type Run } from '../lib/store'
import type { TriageResult } from '../types/triage'
import { NotFoundPage } from './NotFoundPage'

function isTyping(target: EventTarget | null) {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName))
  )
}

function DeleteButton({ onConfirm }: { onConfirm: () => void }) {
  const [armed, setArmed] = useState(false)
  useEffect(() => {
    if (!armed) return
    const timer = window.setTimeout(() => setArmed(false), 4000)
    return () => window.clearTimeout(timer)
  }, [armed])
  return (
    <button
      type="button"
      className={clsx('btn', armed ? 'btn-danger' : 'btn-quiet')}
      onClick={() => (armed ? onConfirm() : setArmed(true))}
    >
      <TrashIcon size={15} />
      {armed ? 'Click to confirm' : 'Delete'}
    </button>
  )
}

function RunWorkspace({ run }: { run: Run }) {
  const navigate = useNavigate()
  const { results } = run.response
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
    <div className="page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/runs">Runs</Link>
        <span aria-hidden="true">/</span>
      </nav>
      <header className="page-header page-header--row">
        <div>
          <h1 className="run-title">{run.name}</h1>
          <p className="page-desc">
            {run.response.total} tickets, {formatRelative(run.createdAt)}. Took{' '}
            {formatDuration(run.response.processing_time_ms)} with <code>{run.response.model}</code>
          </p>
        </div>
        <div className="page-actions">
          <DeleteButton
            onConfirm={() => {
              deleteRun(run.id)
              navigate('/runs')
            }}
          />
          <button type="button" className="btn btn-secondary" onClick={() => exportCSV(results, run.name)}>
            <DownloadSimpleIcon size={15} />
            CSV
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => exportJSONL(results, run.name)}>
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

export function RunPage() {
  const { runId } = useParams()
  const run = useRuns().find((r) => r.id === runId)
  if (!run) {
    return (
      <NotFoundPage
        title="Run not found"
        message="It may have been deleted, or it was created in another browser. Runs are stored locally."
      />
    )
  }
  // Key by id so filters and selection reset when switching runs.
  return <RunWorkspace key={run.id} run={run} />
}
