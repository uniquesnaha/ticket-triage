import type { HealthResponse } from '../types/triage'

export type HealthState = HealthResponse | 'loading' | 'unreachable'

function ModelStatus({ health }: { health: HealthState }) {
  if (health === 'loading') return null
  if (health === 'unreachable') {
    return <span className="status status--bad">API unreachable</span>
  }
  if (!health.llm_configured) {
    return <span className="status status--warn">Model not configured</span>
  }
  return (
    <span className="status status--ok" title="Model used for classification">
      <code>{health.model}</code>
    </span>
  )
}

interface TopBarProps {
  health: HealthState
  onHome: () => void
}

export function TopBar({ health, onHome }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button type="button" className="wordmark" onClick={onHome}>
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="7" />
            <path d="M9 11h14M9 16h9M9 21h5" />
          </svg>
          Triage
        </button>
        <ModelStatus health={health} />
      </div>
    </header>
  )
}
