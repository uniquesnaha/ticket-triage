import { WarningCircleIcon } from '@phosphor-icons/react'
import { useElapsedSeconds } from '../hooks/useTriage'

interface ProcessingViewProps {
  fileName: string
  ticketCount: number | null
  startedAt: number
}

export function ProcessingView({ fileName, ticketCount, startedAt }: ProcessingViewProps) {
  const elapsed = useElapsedSeconds(startedAt)
  const what = ticketCount ? `${ticketCount} tickets` : 'tickets'

  return (
    <section className="page" aria-busy="true" aria-live="polite">
      <header className="page-head">
        <div>
          <h1>Classifying {what}</h1>
          <p className="page-sub">
            <code>{fileName}</code> <span className="muted">{elapsed}s elapsed</span>
          </p>
        </div>
      </header>
      <p className="processing-note">
        Tickets are classified in parallel. A batch of 10 usually takes 10 to 40 seconds,
        longer if the model provider is rate limiting.
      </p>
      <div className="skeleton-table" aria-hidden="true">
        {Array.from({ length: Math.min(ticketCount ?? 6, 8) }, (_, i) => (
          <div key={i} className="skeleton-row" style={{ animationDelay: `${i * 90}ms` }}>
            <span style={{ width: '9%' }} />
            <span style={{ width: '38%' }} />
            <span style={{ width: '13%' }} />
            <span style={{ width: '10%' }} />
            <span style={{ width: '12%' }} />
          </div>
        ))}
      </div>
    </section>
  )
}

interface ErrorViewProps {
  fileName: string
  message: string
  onRetry: () => void
}

export function ErrorView({ fileName, message, onRetry }: ErrorViewProps) {
  return (
    <section className="page">
      <div className="error-panel" role="alert">
        <WarningCircleIcon size={22} weight="fill" className="error-icon" />
        <div>
          <h1>Could not triage {fileName}</h1>
          <p>{message}</p>
          <button type="button" className="btn btn-primary" onClick={onRetry}>
            Choose another file
          </button>
        </div>
      </div>
    </section>
  )
}
