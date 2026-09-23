import { useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { Composer } from '../components/Composer'
import { CsvUpload } from '../components/CsvUpload'
import { ErrorView, ProcessingView } from '../components/StatusViews'
import { useTriageApp } from '../state/TriageContext'

type Mode = 'csv' | 'text'

const MODES: [Mode, string][] = [
  ['csv', 'Upload a CSV'],
  ['text', 'Write a ticket'],
]

export function NewTriagePage() {
  const { job, submitFile, clearJob } = useTriageApp()
  const [mode, setMode] = useState<Mode>('csv')

  return (
    <div className="page page--narrow">
      <header className="page-header">
        <h1>New triage</h1>
        <p className="page-desc">
          Classify tickets by category, priority, sentiment and customer impact, and flag the
          ones a person should look at. <Link to="/how-it-works">How decisions are made</Link>
        </p>
      </header>

      {job?.status === 'processing' ? (
        <ProcessingView
          fileName={job.fileName}
          ticketCount={job.ticketCount}
          startedAt={job.startedAt}
        />
      ) : job?.status === 'error' ? (
        <ErrorView fileName={job.fileName} message={job.message} onRetry={clearJob} />
      ) : (
        <>
          <div className="segmented" role="tablist" aria-label="Input">
            {MODES.map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                id={`tab-${id}`}
                aria-selected={mode === id}
                aria-controls={`panel-${id}`}
                className={clsx('segment', mode === id && 'segment--active')}
                onClick={() => setMode(id)}
              >
                {label}
              </button>
            ))}
          </div>

          <div id="panel-csv" role="tabpanel" aria-labelledby="tab-csv" hidden={mode !== 'csv'}>
            <CsvUpload onFile={submitFile} />
          </div>
          <div id="panel-text" role="tabpanel" aria-labelledby="tab-text" hidden={mode !== 'text'}>
            <Composer />
          </div>
        </>
      )}
    </div>
  )
}
