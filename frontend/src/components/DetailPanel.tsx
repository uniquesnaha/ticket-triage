import { useEffect, useRef } from 'react'
import { CaretDownIcon, CaretUpIcon, XIcon } from '@phosphor-icons/react'
import type { TriageResult } from '../types/triage'
import {
  FIELD_LABEL,
  PREPROCESS_LABEL,
  RULE_LABEL,
  SECURITY_LABEL,
  WARNING_LABEL,
  displayRationale,
  formatDuration,
  formatValue,
} from '../lib/labels'
import { PriorityTag, ReviewTag } from './Tags'

const DECISION_FIELDS = [
  'category',
  'priority',
  'sentiment',
  'customer_impact',
  'needs_human_review',
] as const

interface DetailPanelProps {
  result: TriageResult
  /** "panel" sits beside the queue with navigation; "inline" is embedded in a page. */
  variant?: 'panel' | 'inline'
  onClose?: () => void
  onPrev?: (() => void) | null
  onNext?: (() => void) | null
}

export function DetailPanel({
  result,
  variant = 'panel',
  onClose,
  onPrev = null,
  onNext = null,
}: DetailPanelProps) {
  const panelRef = useRef<HTMLElement>(null)

  useEffect(() => {
    panelRef.current?.scrollTo({ top: 0 })
  }, [result.ticket_id])

  const overrides = new Map(result.field_overrides.map((o) => [o.field, o]))
  const cleanedDiffers = result.cleaned_text.trim() !== result.original_text.trim()
  const checks: { label: string; items: string[] }[] = [
    { label: 'Input warnings', items: result.input_warnings.map((w) => WARNING_LABEL[w] ?? w) },
    { label: 'Security', items: result.security_flags.map((f) => SECURITY_LABEL[f] ?? f) },
    {
      label: 'Rules matched',
      items: result.guardrails_applied.map((r) => RULE_LABEL[r] ?? r),
    },
    {
      label: 'Text cleanup',
      items: result.preprocessing_applied.map((p) => PREPROCESS_LABEL[p] ?? p),
    },
  ].filter((c) => c.items.length > 0)

  return (
    <aside
      className={variant === 'inline' ? 'detail detail--inline' : 'detail'}
      ref={panelRef}
      aria-label={`Ticket ${result.ticket_id}`}
    >
      <header className="detail-head">
        <div className="detail-title">
          <h2>{result.ticket_id}</h2>
          <div className="detail-tags">
            <PriorityTag priority={result.priority} />
            {result.needs_human_review && <ReviewTag />}
          </div>
        </div>
        {variant === 'panel' && (
        <div className="detail-nav">
          <button
            type="button"
            className="icon-btn"
            onClick={onPrev ?? undefined}
            disabled={!onPrev}
            aria-label="Previous ticket"
            title="Previous (k)"
          >
            <CaretUpIcon size={16} />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={onNext ?? undefined}
            disabled={!onNext}
            aria-label="Next ticket"
            title="Next (j)"
          >
            <CaretDownIcon size={16} />
          </button>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close" title="Close (Esc)">
            <XIcon size={16} />
          </button>
        </div>
        )}
      </header>

      <section className="detail-section">
        <h3>Ticket</h3>
        <blockquote className="ticket-body">
          {result.original_text || <span className="muted">This row had no text.</span>}
        </blockquote>
        {cleanedDiffers && result.cleaned_text && (
          <details className="cleaned">
            <summary>Text sent to the model</summary>
            <p>{result.cleaned_text}</p>
          </details>
        )}
      </section>

      <section className="detail-section">
        <h3>Decision</h3>
        <table className="decision">
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Final</th>
              <th scope="col">Model said</th>
            </tr>
          </thead>
          <tbody>
            {DECISION_FIELDS.map((field) => {
              const override = overrides.get(field)
              const model = result.model_judgment
              return (
                <tr key={field} className={override ? 'decision-row--changed' : undefined}>
                  <th scope="row">{FIELD_LABEL[field]}</th>
                  <td>
                    {formatValue(field, result[field])}
                    {override && (
                      <span className="decision-rule">{RULE_LABEL[override.rule] ?? override.rule}</span>
                    )}
                  </td>
                  <td className={override ? 'decision-model--overridden' : 'muted'}>
                    {model ? formatValue(field, model[field]) : 'Not used'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      <section className="detail-section">
        <h3>{result.is_llm_fallback ? 'Why the model was not used' : 'Model rationale'}</h3>
        <p className="rationale">{displayRationale(result.rationale)}</p>
      </section>

      {checks.length > 0 && (
        <section className="detail-section">
          <h3>Checks</h3>
          <dl className="checks">
            {checks.map((c) => (
              <div key={c.label}>
                <dt>{c.label}</dt>
                <dd>
                  <ul>
                    {c.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <footer className="detail-meta">
        <span title={result.prompt_version ? `Prompt ${result.prompt_version}` : undefined}>
          <code>{result.llm_model || 'no model'}</code>
          {result.prompt_version && (
            <code className="muted"> · {result.prompt_version.split('#')[0]}</code>
          )}
        </span>
        <span>{formatDuration(result.processing_time_ms)}</span>
      </footer>
    </aside>
  )
}
