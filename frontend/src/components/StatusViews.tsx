import { WarningCircleIcon } from '@phosphor-icons/react'
import { useElapsedSeconds } from '../state/TriageContext'

interface ProcessingViewProps {
  fileName: string
  ticketCount: number | null
  startedAt: number
}

export function ProcessingView({ fileName, ticketCount, startedAt }: ProcessingViewProps) {
  const elapsed = useElapsedSeconds(startedAt)
  const what = ticketCount ? `${ticketCount} tickets` : 'tickets'

  return (
    <section className="processing" aria-busy="true" aria-live="polite">
      <div className="processing-head">
        <h2>
          Classifying {what} from <code>{fileName}</code>
        </h2>
        <span className="muted tabular">{elapsed}s</span>
      </div>
      <p className="processing-note">
        A batch of 10 usually takes 10 to 40 seconds, longer if the model provider is rate
        limiting. You can leave this page; the run appears in the sidebar when it is done.
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
    <div className="error-panel" role="alert">
      <WarningCircleIcon size={22} weight="fill" className="error-icon" />
      <div>
        <h2>Could not triage {fileName}</h2>
        <p>{message}</p>
        <button type="button" className="btn btn-primary" onClick={onRetry}>
          Try another file
        </button>
      </div>
    </div>
  )
}
