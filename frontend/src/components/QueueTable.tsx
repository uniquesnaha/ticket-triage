import { useMemo, useState } from 'react'
import { CaretDownIcon, CaretUpIcon, MagnifyingGlassIcon } from '@phosphor-icons/react'
import clsx from 'clsx'
import type { Category, TriageResult } from '../types/triage'
import {
  CATEGORY_LABEL,
  IMPACT_LABEL,
  PRIORITY_RANK,
  SENTIMENT_LABEL,
  SOURCE_LABEL,
  decisionSource,
} from '../lib/labels'
import { PriorityTag, ReviewTag } from './Tags'

type View = 'all' | 'review' | 'adjusted' | 'fallback'
type SortKey = 'priority' | 'ticket_id' | 'category'

const VIEWS: { id: View; label: string; test: (r: TriageResult) => boolean }[] = [
  { id: 'all', label: 'All', test: () => true },
  { id: 'review', label: 'Needs review', test: (r) => r.needs_human_review },
  { id: 'adjusted', label: 'Adjusted by rules', test: (r) => r.field_overrides.length > 0 },
  { id: 'fallback', label: 'Model not used', test: (r) => r.is_llm_fallback },
]

interface QueueTableProps {
  results: TriageResult[]
  selected: TriageResult | null
  onSelect: (result: TriageResult) => void
}

export function useQueue(results: TriageResult[]) {
  const [view, setView] = useState<View>('all')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<Category | 'all'>('all')
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'priority', desc: true })

  const visible = useMemo(() => {
    const test = VIEWS.find((v) => v.id === view)!.test
    const q = query.trim().toLowerCase()
    const rows = results.filter(
      (r) =>
        test(r) &&
        (category === 'all' || r.category === category) &&
        (!q || r.ticket_id.toLowerCase().includes(q) || r.original_text.toLowerCase().includes(q)),
    )
    const dir = sort.desc ? -1 : 1
    return rows.sort((a, b) => {
      const byId = a.ticket_id.localeCompare(b.ticket_id, undefined, { numeric: true })
      const primary =
        sort.key === 'priority'
          ? PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]
          : sort.key === 'category'
            ? a.category.localeCompare(b.category)
            : byId
      return dir * primary || byId
    })
  }, [results, view, query, category, sort])

  return { view, setView, query, setQuery, category, setCategory, sort, setSort, visible }
}

type QueueState = ReturnType<typeof useQueue>

export function QueueTable({
  results,
  selected,
  onSelect,
  queue,
}: QueueTableProps & { queue: QueueState }) {
  const { view, setView, query, setQuery, category, setCategory, sort, setSort, visible } = queue
  const categories = useMemo(
    () => [...new Set(results.map((r) => r.category))].sort(),
    [results],
  )

  const toggleSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: key === 'priority' }))

  const sortHeader = (id: SortKey, label: string) => (
    <th aria-sort={sort.key === id ? (sort.desc ? 'descending' : 'ascending') : 'none'}>
      <button type="button" className="th-sort" onClick={() => toggleSort(id)}>
        {label}
        {sort.key === id &&
          (sort.desc ? <CaretDownIcon size={12} weight="bold" /> : <CaretUpIcon size={12} weight="bold" />)}
      </button>
    </th>
  )

  return (
    <section className="queue" aria-label="Triaged tickets">
      <div className="queue-toolbar">
        <div className="segmented" role="tablist" aria-label="Filter tickets">
          {VIEWS.map((v) => {
            const count = results.filter(v.test).length
            if (v.id === 'fallback' && count === 0) return null
            return (
              <button
                key={v.id}
                type="button"
                role="tab"
                aria-selected={view === v.id}
                className={clsx('segment', view === v.id && 'segment--active')}
                onClick={() => setView(v.id)}
              >
                {v.label}
                <span className="segment-count">{count}</span>
              </button>
            )
          })}
        </div>
        <div className="queue-filters">
          <label className="search">
            <MagnifyingGlassIcon size={15} aria-hidden="true" />
            <input
              type="search"
              placeholder="Search ID or text"
              aria-label="Search tickets"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select
            className="select"
            aria-label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value as Category | 'all')}
          >
            <option value="all">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              {sortHeader('ticket_id', 'ID')}
              <th>Ticket</th>
              {sortHeader('category', 'Category')}
              {sortHeader('priority', 'Priority')}
              <th className="hide-md">Sentiment</th>
              <th className="hide-md">Impact</th>
              <th>Review</th>
              <th className="hide-lg">Decided by</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => {
              const source = decisionSource(r)
              return (
                <tr
                  key={`${r.ticket_id}:${results.indexOf(r)}`}
                  className={clsx(selected === r && 'row--selected')}
                  onClick={() => onSelect(r)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(r)
                    }
                  }}
                  tabIndex={0}
                  aria-selected={selected === r}
                >
                  <td className="cell-id">{r.ticket_id}</td>
                  <td className="cell-text">
                    {r.original_text || <span className="muted">No text</span>}
                  </td>
                  <td className="cell-category">{CATEGORY_LABEL[r.category]}</td>
                  <td className="cell-priority">
                    <PriorityTag priority={r.priority} />
                  </td>
                  <td className="hide-md">{SENTIMENT_LABEL[r.sentiment]}</td>
                  <td className="hide-md">{IMPACT_LABEL[r.customer_impact]}</td>
                  <td className="cell-review">
                    {r.needs_human_review ? <ReviewTag /> : <span className="muted">No</span>}
                  </td>
                  <td className={clsx('hide-lg', 'cell-source', `cell-source--${source}`)}>
                    {SOURCE_LABEL[source]}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {visible.length === 0 && (
          <p className="table-empty">No tickets match these filters.</p>
        )}
      </div>
    </section>
  )
}
