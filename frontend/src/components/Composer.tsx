import { useState, type FormEvent, type KeyboardEvent } from 'react'
import clsx from 'clsx'
import { useSingleTicket } from '../hooks/useSingleTicket'
import { CATEGORY_LABEL } from '../lib/labels'
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
  const { history, pending, error, classify } = useSingleTicket()
  const [text, setText] = useState('')
  const [shown, setShown] = useState(0)

  const submit = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!text.trim() || pending) return
    if (await classify(text.trim())) setShown(0)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
  }

  const current = history[shown]

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

      {history.length > 1 && (
        <section className="composer-history" aria-label="Earlier tickets">
          <h2>Earlier this session</h2>
          <ul>
            {history.map((r, i) => (
              <li key={r.ticket_id}>
                <button
                  type="button"
                  className={clsx('history-row', i === shown && 'history-row--active')}
                  onClick={() => setShown(i)}
                >
                  <span className="history-text">{r.original_text}</span>
                  <span className="history-meta">
                    {CATEGORY_LABEL[r.category]}
                    <PriorityTag priority={r.priority} />
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
