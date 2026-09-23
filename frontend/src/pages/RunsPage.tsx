import { Link, useNavigate } from 'react-router-dom'
import { PlusIcon, StackIcon } from '@phosphor-icons/react'
import { formatRelative, useRuns } from '../lib/store'

export function RunsPage() {
  const runs = useRuns()
  const navigate = useNavigate()

  return (
    <div className="page">
      <header className="page-header page-header--row">
        <div>
          <h1>Runs</h1>
          <p className="page-desc">Every CSV you triage is kept here, in this browser.</p>
        </div>
        <Link to="/" className="btn btn-primary">
          <PlusIcon size={15} weight="bold" />
          New triage
        </Link>
      </header>

      {runs.length === 0 ? (
        <div className="empty">
          <StackIcon size={28} weight="light" className="empty-icon" />
          <h2>No runs yet</h2>
          <p>Upload a CSV or try the sample file to create your first run.</p>
          <Link to="/" className="btn btn-secondary">
            Start a triage
          </Link>
        </div>
      ) : (
        <div className="table-scroll">
          <table className="table table--runs">
            <thead>
              <tr>
                <th>Run</th>
                <th className="num">Tickets</th>
                <th className="num">Need review</th>
                <th className="num hide-sm">Critical or high</th>
                <th className="num hide-md">Adjusted by rules</th>
                <th className="num hide-md">Model not used</th>
                <th className="hide-sm">Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const results = run.response.results
                const urgent = results.filter(
                  (r) => r.priority === 'critical' || r.priority === 'high',
                ).length
                const adjusted = results.filter((r) => r.field_overrides.length > 0).length
                const fallback = results.filter((r) => r.is_llm_fallback).length
                const open = () => navigate(`/runs/${run.id}`)
                return (
                  <tr
                    key={run.id}
                    tabIndex={0}
                    onClick={open}
                    onKeyDown={(e) => e.key === 'Enter' && open()}
                  >
                    <td className="cell-run">{run.name}</td>
                    <td className="num">{run.response.total}</td>
                    <td className="num">{run.response.needs_human_review_count}</td>
                    <td className="num hide-sm">{urgent}</td>
                    <td className="num hide-md">{adjusted}</td>
                    <td className={fallback ? 'num hide-md text-warn' : 'num hide-md'}>{fallback}</td>
                    <td className="muted hide-sm">{formatRelative(run.createdAt)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
