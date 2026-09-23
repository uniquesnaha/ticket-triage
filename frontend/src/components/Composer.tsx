import { useState, type FormEvent, type KeyboardEvent } from 'react'
import clsx from 'clsx'
import { api } from '../api/client'
import { CATEGORY_LABEL } from '../lib/labels'
import { clearQuickChecks, formatRelative, saveQuickCheck, useQuickChecks } from '../lib/store'
import { DetailPanel } from './DetailPanel'
import { PriorityTag } from './Tags'

const MAX_LENGTH = 2000
const SHORTCUT = /Mac|iPhone|iPad/.test(navigator.userAgent) ? '⌘ Enter' : 'Ctrl Enter'

const EXAMPLES = [
  {
    label: 'Billing',
    text: 'We were billed for 12 seats but only have 9 users. Can you fix the invoice?',
  },
  {
    label: 'Outage',
    text: 'Checkout has been failing for all our EU customers since 9am. We are losing orders.',
  },
  {
    label: 'Feature idea',
    text: 'Would be great if exports could include the ticket tags as a column.',
  },
]

export function Composer() {
  const history = useQuickChecks()
  const [text, setText] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shownId, setShownId] = useState<string | null>(null)

  const submit = async (e?: FormEvent) => {
    e?.preventDefault()
    const body = text.trim()
    if (!body || pending) return
    setPending(true)
    setError(null)
    try {
      const ticketId = `Q-${Date.now().toString(36).toUpperCase()}`
      const response = await api.triageTickets([{ ticket_id: ticketId, text: body }])
      saveQuickCheck(response.results[0])
      setShownId(ticketId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.')
    } finally {
      setPending(false)
    }
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
  }

  const current = history.find((r) => r.ticket_id === shownId) ?? null

  return (
    <div className="composer">
      <form onSubmit={submit}>
        <label htmlFor="ticket-text" className="field-label">
          Ticket text
        </label>
        <textarea
          id="ticket-text"
          className="textarea"
          rows={5}
          maxLength={MAX_LENGTH}
          placeholder="Paste or type a customer message"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={pending}
        />
        <div className="composer-bar">
          <div className="composer-examples">
            <span className="muted">Try:</span>
            {EXAMPLES.map((example) => (
              <button
                key={example.label}
                type="button"
                className="link-btn"
                onClick={() => setText(example.text)}
                disabled={pending}
              >
                {example.label}
              </button>
            ))}
          </div>
          <div className="composer-submit">
            <span className="muted counter">
              {text.length}/{MAX_LENGTH}
            </span>
            <button type="submit" className="btn btn-primary" disabled={!text.trim() || pending}>
              {pending ? 'Classifying' : 'Classify'}
              {!pending && <kbd>{SHORTCUT}</kbd>}
            </button>
          </div>
        </div>
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
      </form>

      {pending && (
        <div className="composer-pending" aria-live="polite">
          <span className="skeleton-line" />
          <span className="skeleton-line skeleton-line--short" />
        </div>
      )}

      {current && !pending && (
        <div className="composer-result">
          <DetailPanel result={current} variant="inline" />
        </div>
      )}

      {history.length > 0 && (
        <section className="composer-history" aria-label="Recent quick checks">
          <div className="section-head">
            <h2>Recent quick checks</h2>
            <button type="button" className="link-btn" onClick={clearQuickChecks}>
              Clear
            </button>
          </div>
          <ul>
            {history.map((r) => (
              <li key={r.ticket_id}>
                <button
                  type="button"
                  className={clsx('history-row', r.ticket_id === shownId && 'history-row--active')}
                  onClick={() => setShownId(r.ticket_id)}
                >
                  <span className="history-text">{r.original_text}</span>
                  <span className="history-meta">
                    <span className="hide-sm">{CATEGORY_LABEL[r.category]}</span>
                    <PriorityTag priority={r.priority} />
                    <span className="muted hide-sm">{formatRelative(r.processed_at)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
