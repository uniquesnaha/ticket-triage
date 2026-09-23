import { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronUp, ChevronDown, AlertTriangle } from 'lucide-react'
import type { TriageResult, Priority, Category } from '../types/triage'
import { PriorityBadge, CategoryBadge, SentimentBadge, ReviewBadge } from './Badge'

interface ResultsTableProps {
  results: TriageResult[]
  onRowClick: (result: TriageResult) => void
}

type SortKey = 'ticket_id' | 'priority' | 'category' | 'sentiment'
type SortDir = 'asc' | 'desc'

const PRIORITY_RANK: Record<Priority, number> = {
  critical: 4, high: 3, medium: 2, low: 1,
}

export function ResultsTable({ results, onRowClick }: ResultsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('priority')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [filterCategory, setFilterCategory] = useState<Category | 'all'>('all')
  const [filterReview, setFilterReview] = useState<boolean | null>(null)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  const filtered = results
    .filter((r) => filterCategory === 'all' || r.category === filterCategory)
    .filter((r) => filterReview === null || r.needs_human_review === filterReview)
    .sort((a, b) => {
      let cmp = 0
      if (sortKey === 'priority') cmp = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]
      else if (sortKey === 'ticket_id') cmp = a.ticket_id.localeCompare(b.ticket_id)
      else if (sortKey === 'category') cmp = a.category.localeCompare(b.category)
      else if (sortKey === 'sentiment') cmp = a.sentiment.localeCompare(b.sentiment)
      return sortDir === 'asc' ? cmp : -cmp
    })

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return null
    return sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
  }

  const categories = Array.from(new Set(results.map((r) => r.category)))

  return (
    <div className="results-table-wrap">
      {/* Filters */}
      <div className="table-filters">
        <select
          className="filter-select"
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value as Category | 'all')}
        >
          <option value="all">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c.replace('_', ' ')}</option>
          ))}
        </select>
        <select
          className="filter-select"
          value={filterReview === null ? 'all' : filterReview ? 'yes' : 'no'}
          onChange={(e) =>
            setFilterReview(e.target.value === 'all' ? null : e.target.value === 'yes')
          }
        >
          <option value="all">All Review Status</option>
          <option value="yes">Needs Review</option>
          <option value="no">Auto-resolved</option>
        </select>
        <span className="filter-count">{filtered.length} of {results.length} tickets</span>
      </div>

      {/* Table */}
      <div className="table-container">
        <table className="results-table">
          <thead>
            <tr>
              {([
                ['ticket_id', 'Ticket ID'],
                ['priority', 'Priority'],
                ['category', 'Category'],
                ['sentiment', 'Sentiment'],
              ] as [SortKey, string][]).map(([key, label]) => (
                <th key={key} onClick={() => toggleSort(key)} className="table-th sortable">
                  <span className="th-content">
                    {label} <SortIcon col={key} />
                  </span>
                </th>
              ))}
              <th className="table-th">Review</th>
              <th className="table-th">Guardrails</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((result, idx) => (
              <motion.tr
                key={result.ticket_id}
                className={`table-row ${result.priority === 'critical' ? 'table-row--critical' : ''}`}
                onClick={() => onRowClick(result)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
                whileHover={{ backgroundColor: 'rgba(99, 102, 241, 0.07)' }}
              >
                <td className="table-td">
                  <span className="ticket-id-cell">
                    {result.security_flags.length > 0 && (
                      <AlertTriangle size={14} className="flag-icon" />
                    )}
                    {result.ticket_id}
                  </span>
                </td>
                <td className="table-td"><PriorityBadge priority={result.priority} /></td>
                <td className="table-td"><CategoryBadge category={result.category} /></td>
                <td className="table-td"><SentimentBadge sentiment={result.sentiment} /></td>
                <td className="table-td">
                  {result.needs_human_review ? (
                    <ReviewBadge needsReview />
                  ) : (
                    <span className="auto-resolved">✓ Auto</span>
                  )}
                </td>
                <td className="table-td">
                  <span className="guardrail-count">
                    {result.guardrails_applied.length > 0
                      ? `${result.guardrails_applied.length} rule${result.guardrails_applied.length > 1 ? 's' : ''}`
                      : '—'}
                  </span>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
