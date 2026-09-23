import { useCallback, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Download, RefreshCw } from 'lucide-react'
import type { TriageResult, TriageBatchResponse } from './types/triage'
import { accessKey } from './api/client'
import { AccessKeyForm } from './components/AccessKeyForm'
import { Header } from './components/Header'
import { UploadZone } from './components/UploadZone'
import { ProgressTracker } from './components/ProgressTracker'
import { StatsPanel } from './components/StatsPanel'
import { ResultsTable } from './components/ResultsTable'
import { TicketCard } from './components/TicketCard'
import { useTriage } from './hooks/useTriage'
import './styles/index.css'

function saveFile(content: string, type: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadJSON(response: TriageBatchResponse) {
  saveFile(JSON.stringify(response.results, null, 2), 'application/json', 'triage_results.json')
}

// RFC 4180 quoting, plus neutralising leading =,+,-,@ so spreadsheet apps don't
// execute ticket text as a formula (CSV injection).
function csvCell(value: unknown): string {
  let text = String(value)
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function downloadCSV(results: TriageResult[]) {
  const headers = [
    'ticket_id', 'category', 'priority', 'sentiment', 'customer_impact',
    'needs_human_review', 'guardrails_applied', 'preprocessing_applied',
    'security_flags', 'input_warnings', 'is_llm_fallback', 'processing_time_ms', 'rationale',
  ]
  const rows = results.map((r) =>
    [
      r.ticket_id, r.category, r.priority, r.sentiment, r.customer_impact,
      r.needs_human_review, r.guardrails_applied.join('|'), r.preprocessing_applied.join('|'),
      r.security_flags.join('|'), r.input_warnings.join('|'), r.is_llm_fallback,
      r.processing_time_ms, r.rationale,
    ].map(csvCell).join(','),
  )
  saveFile([headers.join(','), ...rows].join('\r\n'), 'text/csv', 'triage_results.csv')
}

export default function App() {
  const [hasKey, setHasKey] = useState(() => Boolean(accessKey.get()))
  const handleUnauthorized = useCallback(() => setHasKey(false), [])
  const { status, response, error, uploadCSV, reset } = useTriage(handleUnauthorized)
  const [selectedResult, setSelectedResult] = useState<TriageResult | null>(null)
  const [fileName, setFileName] = useState('')

  const saveKey = (key: string) => {
    accessKey.set(key)
    setHasKey(true)
  }

  const forgetKey = () => {
    accessKey.clear()
    setHasKey(false)
  }

  const handleFile = (file: File) => {
    setFileName(file.name)
    uploadCSV(file)
  }

  return (
    <div className="app">
      <Header />

      <main className="main">
        <AnimatePresence mode="wait">
          {/* Idle: upload zone */}
          {status === 'idle' && (
            <motion.div
              key="upload"
              className="upload-page"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="upload-hero">
                <h2 className="hero-title">Triage Support Tickets with AI</h2>
                <p className="hero-subtitle">
                  Upload a CSV file and get structured triage results — category, priority,
                  sentiment, customer impact, and human review flags — in seconds.
                </p>
              </div>
              {hasKey ? (
                <>
                  <UploadZone onFile={handleFile} />
                  <div className="sample-hint">
                    <p>
                      Need a test file?{' '}
                      <a href="/project_1.csv" download className="sample-link">
                        Download sample CSV ↓
                      </a>
                      {' · '}
                      <button type="button" className="link-button" onClick={forgetKey}>
                        Change access key
                      </button>
                    </p>
                  </div>
                </>
              ) : (
                <AccessKeyForm onSubmit={saveKey} />
              )}
            </motion.div>
          )}

          {/* Processing */}
          {status === 'processing' && (
            <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <ProgressTracker fileName={fileName} />
            </motion.div>
          )}

          {/* Error */}
          {status === 'error' && (
            <motion.div
              key="error"
              className="error-card"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <h3 className="error-title">Processing Failed</h3>
              <p className="error-message">{error}</p>
              <button className="btn btn-secondary" onClick={reset}>
                <RefreshCw size={16} /> Try Again
              </button>
            </motion.div>
          )}

          {/* Success: results dashboard */}
          {status === 'success' && response && (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Toolbar */}
              <div className="results-toolbar">
                <h2 className="results-heading">Triage Results</h2>
                <div className="results-actions">
                  <button className="btn btn-ghost" onClick={reset}>
                    <RefreshCw size={16} /> New Upload
                  </button>
                  <button className="btn btn-secondary" onClick={() => downloadCSV(response.results)}>
                    <Download size={16} /> Download CSV
                  </button>
                  <button className="btn btn-primary" onClick={() => downloadJSON(response)}>
                    <Download size={16} /> Download JSON
                  </button>
                </div>
              </div>

              <StatsPanel response={response} />

              <div className="table-section">
                <h3 className="section-title">All Tickets</h3>
                <ResultsTable results={response.results} onRowClick={setSelectedResult} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Ticket detail drawer */}
      <TicketCard result={selectedResult} onClose={() => setSelectedResult(null)} />
    </div>
  )
}
