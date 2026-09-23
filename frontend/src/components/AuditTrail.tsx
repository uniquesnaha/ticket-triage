import type { TriageResult } from '../types/triage'
import { SecurityFlagBadge } from './Badge'

interface AuditTrailProps {
  result: TriageResult
}

const fmt = (value: string | boolean) => String(value).replace(/_/g, ' ')

export function AuditTrail({ result }: AuditTrailProps) {
  const hasPreprocessing = result.preprocessing_applied.length > 0
  const hasGuardrails = result.guardrails_applied.length > 0
  const hasFlags = result.security_flags.length > 0
  const hasWarnings = result.input_warnings.length > 0

  if (!hasPreprocessing && !hasGuardrails && !hasFlags && !hasWarnings && !result.is_llm_fallback) {
    return (
      <div className="audit-empty">
        <span>✓ No preprocessing or guardrail overrides applied.</span>
        <span className="audit-model-tag">[MODEL]</span>
      </div>
    )
  }

  return (
    <div className="audit-trail">
      {hasFlags && (
        <div className="audit-section audit-section--security">
          <h4 className="audit-section-title">🚨 Security Events</h4>
          <div className="audit-tags">
            {result.security_flags.map((flag) => (
              <SecurityFlagBadge key={flag} flag={flag} />
            ))}
          </div>
        </div>
      )}

      {hasWarnings && (
        <div className="audit-section audit-section--fallback">
          <h4 className="audit-section-title">📋 Input Data Warnings</h4>
          <div className="audit-tags">
            {result.input_warnings.map((w) => (
              <span key={w} className="audit-tag audit-tag--pre">{w}</span>
            ))}
          </div>
        </div>
      )}

      {hasPreprocessing && (
        <div className="audit-section">
          <h4 className="audit-section-title">🔧 Preprocessing Applied</h4>
          <div className="audit-tags">
            {result.preprocessing_applied.map((t) => (
              <span key={t} className="audit-tag audit-tag--pre">{t}</span>
            ))}
          </div>
        </div>
      )}

      {hasGuardrails && (
        <div className="audit-section">
          <h4 className="audit-section-title">⚖️ Guardrails Applied</h4>
          <div className="audit-tags">
            {result.guardrails_applied.map((r) => (
              <span key={r} className="audit-tag audit-tag--rule">{r}</span>
            ))}
          </div>
          {result.field_overrides.map((o) => (
            <p key={o.field} className="audit-override">
              <code>{o.field}</code>: model said <strong>{fmt(o.model_value)}</strong> → rule set{' '}
              <strong>{fmt(o.final_value)}</strong> ({o.rule})
            </p>
          ))}
          <p className="audit-note">
            {result.field_overrides.length > 0
              ? 'Fields above were changed by deterministic rules, not the model.'
              : 'Rules fired but agreed with the model; no fields changed.'}
          </p>
        </div>
      )}

      {result.is_llm_fallback && (
        <div className="audit-section audit-section--fallback">
          <h4 className="audit-section-title">⚠️ Model Not Used</h4>
          <p className="audit-note">
            This result is a deterministic safe default, not a model judgment. The rationale
            explains why.
          </p>
        </div>
      )}
    </div>
  )
}
