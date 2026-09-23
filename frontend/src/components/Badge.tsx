import type { Category, Priority, Sentiment, SecurityFlag } from '../types/triage'
import clsx from 'clsx'

// ── Priority Badge ─────────────────────────────────────────────────────────

const priorityConfig: Record<Priority, { label: string; className: string }> = {
  critical: { label: 'CRITICAL', className: 'badge-critical' },
  high: { label: 'HIGH', className: 'badge-high' },
  medium: { label: 'MEDIUM', className: 'badge-medium' },
  low: { label: 'LOW', className: 'badge-low' },
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const config = priorityConfig[priority]
  return <span className={clsx('badge', config.className)}>{config.label}</span>
}

// ── Category Badge ─────────────────────────────────────────────────────────

const categoryConfig: Record<Category, { label: string; icon: string }> = {
  billing: { label: 'Billing', icon: '💳' },
  auth: { label: 'Auth', icon: '🔐' },
  outage: { label: 'Outage', icon: '🔴' },
  feature_request: { label: 'Feature Request', icon: '✨' },
  shipping: { label: 'Shipping', icon: '📦' },
  security: { label: 'Security', icon: '🛡️' },
  bug: { label: 'Bug', icon: '🐛' },
  spam: { label: 'Spam', icon: '🚫' },
  unknown: { label: 'Unknown', icon: '❓' },
}

export function CategoryBadge({ category }: { category: Category }) {
  const config = categoryConfig[category]
  return (
    <span className="badge badge-category">
      {config.icon} {config.label}
    </span>
  )
}

// ── Sentiment Badge ────────────────────────────────────────────────────────

const sentimentConfig: Record<Sentiment, { label: string; className: string }> = {
  urgent: { label: 'Urgent', className: 'badge-urgent' },
  negative: { label: 'Negative', className: 'badge-negative' },
  neutral: { label: 'Neutral', className: 'badge-neutral' },
  positive: { label: 'Positive', className: 'badge-positive' },
}

export function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  const config = sentimentConfig[sentiment]
  return <span className={clsx('badge', config.className)}>{config.label}</span>
}

// ── Review Badge ───────────────────────────────────────────────────────────

export function ReviewBadge({ needsReview }: { needsReview: boolean }) {
  if (!needsReview) return null
  return <span className="badge badge-review">👤 Needs Review</span>
}

// ── Security Flag Badge ────────────────────────────────────────────────────

const flagLabels: Record<SecurityFlag, string> = {
  injection_attempt: '⚠️ Injection Attempt',
  excessive_length: '📏 Excessive Length',
  unicode_anomaly: '🔤 Unicode Anomaly',
}

export function SecurityFlagBadge({ flag }: { flag: SecurityFlag }) {
  return <span className="badge badge-security-flag">{flagLabels[flag]}</span>
}
