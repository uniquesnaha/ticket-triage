import { motion, AnimatePresence } from 'framer-motion'
import { X, Clock } from 'lucide-react'
import type { TriageResult } from '../types/triage'
import { PriorityBadge, CategoryBadge, SentimentBadge, ReviewBadge } from './Badge'
import { AuditTrail } from './AuditTrail'

interface TicketCardProps {
  result: TriageResult | null
  onClose: () => void
}

export function TicketCard({ result, onClose }: TicketCardProps) {
  return (
    <AnimatePresence>
      {result && (
        <>
          {/* Backdrop */}
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          {/* Drawer */}
          <motion.div
            className="ticket-drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 260 }}
          >
            {/* Header */}
            <div className="drawer-header">
              <div>
                <h2 className="drawer-ticket-id">{result.ticket_id}</h2>
                <div className="drawer-badges">
                  <PriorityBadge priority={result.priority} />
                  <CategoryBadge category={result.category} />
                  <SentimentBadge sentiment={result.sentiment} />
                  <ReviewBadge needsReview={result.needs_human_review} />
                </div>
              </div>
              <button className="drawer-close" onClick={onClose} aria-label="Close">
                <X size={20} />
              </button>
            </div>

            <div className="drawer-body">
              {/* Ticket Text */}
              <section className="drawer-section">
                <h3 className="drawer-section-title">Original Ticket</h3>
                <div className="ticket-text ticket-text--original">{result.original_text}</div>
              </section>

              {result.cleaned_text !== result.original_text && (
                <section className="drawer-section">
                  <h3 className="drawer-section-title">Cleaned Text</h3>
                  <div className="ticket-text ticket-text--cleaned">{result.cleaned_text}</div>
                </section>
              )}

              {/* Classification */}
              <section className="drawer-section">
                <h3 className="drawer-section-title">Classification Details</h3>
                <div className="classification-grid">
                  <div className="classification-item">
                    <span className="classification-label">Customer Impact</span>
                    <span className="classification-value">
                      {result.customer_impact.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="classification-item">
                    <span className="classification-label">Processing Time</span>
                    <span className="classification-value">
                      <Clock size={12} style={{ display: 'inline', marginRight: 4 }} />
                      {result.processing_time_ms}ms
                    </span>
                  </div>
                  <div className="classification-item">
                    <span className="classification-label">LLM Model</span>
                    <span className="classification-value">{result.llm_model || 'N/A'}</span>
                  </div>
                  <div className="classification-item">
                    <span className="classification-label">LLM Fallback</span>
                    <span className="classification-value">
                      {result.is_llm_fallback ? '⚠️ Yes' : '✓ No'}
                    </span>
                  </div>
                </div>
              </section>

              {/* Rationale */}
              <section className="drawer-section">
                <h3 className="drawer-section-title">Rationale</h3>
                <p className="rationale-text">{result.rationale}</p>
              </section>

              {/* Audit Trail */}
              <section className="drawer-section">
                <h3 className="drawer-section-title">Audit Trail</h3>
                <AuditTrail result={result} />
              </section>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
