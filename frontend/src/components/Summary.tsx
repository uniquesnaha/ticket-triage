import type { TriageResult } from '../types/triage'
import { PRIORITIES, PRIORITY_LABEL } from '../lib/labels'

export function Summary({ results }: { results: TriageResult[] }) {
  const total = results.length
  const review = results.filter((r) => r.needs_human_review).length
  const urgent = results.filter((r) => r.priority === 'critical' || r.priority === 'high').length
  const adjusted = results.filter((r) => r.field_overrides.length > 0).length
  const fallback = results.filter((r) => r.is_llm_fallback).length
  const byPriority = PRIORITIES.map((p) => ({
    priority: p,
    count: results.filter((r) => r.priority === p).length,
  }))

  return (
    <section className="summary" aria-label="Batch summary">
      <dl className="summary-stats">
        <div>
          <dt>Need review</dt>
          <dd>
            {review}
            <span className="muted"> of {total}</span>
          </dd>
        </div>
        <div>
          <dt>Critical or high</dt>
          <dd>{urgent}</dd>
        </div>
        <div>
          <dt>Adjusted by rules</dt>
          <dd>{adjusted}</dd>
        </div>
        <div>
          <dt>Model not used</dt>
          <dd className={fallback > 0 ? 'text-warn' : undefined}>{fallback}</dd>
        </div>
      </dl>

      <div className="priority-mix">
        <div className="priority-mix-bar" role="img" aria-label="Tickets by priority">
          {byPriority
            .filter((p) => p.count > 0)
            .map((p) => (
              <span
                key={p.priority}
                className={`mix mix--${p.priority}`}
                style={{ flexGrow: p.count }}
              />
            ))}
        </div>
        <ul className="priority-mix-legend">
          {byPriority.map((p) => (
            <li key={p.priority}>
              <span className={`swatch mix--${p.priority}`} aria-hidden="true" />
              {PRIORITY_LABEL[p.priority]} <strong>{p.count}</strong>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
