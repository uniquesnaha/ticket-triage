import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { BookOpenTextIcon, ListIcon, PlusIcon, StackIcon, XIcon } from '@phosphor-icons/react'
import clsx from 'clsx'
import { formatRelative, useRuns } from '../lib/store'
import { useTriageApp, type HealthState } from '../state/TriageContext'

function Brand() {
  return (
    <span className="brand">
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" />
        <path d="M9 11h14M9 16h9M9 21h5" />
      </svg>
      Triage
    </span>
  )
}

function ModelStatus({ health }: { health: HealthState }) {
  if (health === 'loading') return <span className="status status--idle">Checking model</span>
  if (health === 'unreachable') return <span className="status status--bad">API unreachable</span>
  if (!health.llm_configured) return <span className="status status--warn">Model not configured</span>
  return (
    <span className="status status--ok" title="Model used for classification">
      <code>{health.model}</code>
    </span>
  )
}

export function AppShell() {
  const { health, job } = useTriageApp()
  const runs = useRuns()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => setMenuOpen(false), [location.pathname])

  const navClass = ({ isActive }: { isActive: boolean }) =>
    clsx('nav-item', isActive && 'nav-item--active')

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <header className="mobilebar">
        <button
          type="button"
          className="icon-btn"
          onClick={() => setMenuOpen(true)}
          aria-label="Open navigation"
        >
          <ListIcon size={20} />
        </button>
        <Brand />
      </header>

      <aside className={clsx('sidebar', menuOpen && 'sidebar--open')} aria-label="Navigation">
        <div className="sidebar-top">
          <Brand />
          <button
            type="button"
            className="icon-btn sidebar-close"
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation"
          >
            <XIcon size={18} />
          </button>
        </div>

        <nav className="nav">
          <NavLink to="/" end className={navClass}>
            <PlusIcon size={17} />
            New triage
          </NavLink>
          <NavLink to="/runs" end className={navClass}>
            <StackIcon size={17} />
            Runs
            {runs.length > 0 && <span className="nav-count">{runs.length}</span>}
          </NavLink>
          <NavLink to="/how-it-works" className={navClass}>
            <BookOpenTextIcon size={17} />
            How it works
          </NavLink>
        </nav>

        {(job || runs.length > 0) && (
          <div className="sidebar-section">
            <h2 className="sidebar-heading">Recent runs</h2>
            <ul className="recent">
              {job?.status === 'processing' && (
                <li>
                  <NavLink to="/" end className="recent-item recent-item--pending">
                    <span className="recent-name">{job.fileName}</span>
                    <span className="recent-meta">Classifying</span>
                  </NavLink>
                </li>
              )}
              {runs.slice(0, 6).map((run) => (
                <li key={run.id}>
                  <NavLink
                    to={`/runs/${run.id}`}
                    className={({ isActive }) => clsx('recent-item', isActive && 'recent-item--active')}
                  >
                    <span className="recent-name">{run.name}</span>
                    <span className="recent-meta">{formatRelative(run.createdAt)}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="sidebar-footer">
          <ModelStatus health={health} />
          <p>Runs are saved in this browser only.</p>
        </div>
      </aside>

      {menuOpen && <div className="scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" />}

      <main id="main" className="content">
        <Outlet />
      </main>
    </div>
  )
}
