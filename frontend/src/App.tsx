import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Download, RefreshCw } from 'lucide-react'
import type { TriageResult, TriageBatchResponse } from './types/triage'
import { Header } from './components/Header'
import { UploadZone } from './components/UploadZone'
import { ProgressTracker } from './components/ProgressTracker'
import { StatsPanel } from './components/StatsPanel'
import { ResultsTable } from './components/ResultsTable'
import { TicketCard } from './components/TicketCard'
import { useTriage } from './hooks/useTriage'
import './styles/index.css'

function downloadJSON(response: TriageBatchResponse) {
  const blob = new Blob([JSON.stringify(response.results, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'triage_results.json'
  a.click()
  URL.revokeObjectURL(url)
}

function downloadCSV(results: TriageResult[]) {
  const headers = [
    'ticket_id', 'category', 'priority', 'sentiment', 'customer_impact',
    'needs_human_review', 'guardrails_applied', 'preprocessing_applied',
    'security_flags', 'is_llm_fallback', 'processing_time_ms', 'rationale',
  ]
  const rows = results.map((r) =>
    [
      r.ticket_id, r.category, r.priority, r.sentiment, r.customer_impact,
      r.needs_human_review, r.guardrails_applied.join('|'), r.preprocessing_applied.join('|'),
      r.security_flags.join('|'), r.is_llm_fallback, r.processing_time_ms,
      `"${r.rationale.replace(/"/g, '""')}"`,
    ].join(',')
  )
  const csv = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'triage_results.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function App() {
  const { status, response, error, uploadCSV, reset } = useTriage()
  const [selectedResult, setSelectedResult] = useState<TriageResult | null>(null)
  const [fileName, setFileName] = useState('')

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
              <UploadZone onFile={handleFile} />
              <div className="sample-hint">
                <p>
                  Need a test file?{' '}
                  <a href="/project_1.csv" download className="sample-link">
                    Download sample CSV ↓
                  </a>
                </p>
              </div>
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
