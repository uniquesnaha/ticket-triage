import type { TriageResult } from '../types/triage'
import { SecurityFlagBadge } from './Badge'

interface AuditTrailProps {
  result: TriageResult
}

export function AuditTrail({ result }: AuditTrailProps) {
  const hasPreprocessing = result.preprocessing_applied.length > 0
  const hasGuardrails = result.guardrails_applied.length > 0
  const hasFlags = result.security_flags.length > 0

  if (!hasPreprocessing && !hasGuardrails && !hasFlags) {
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
          <p className="audit-note">
            These fields were overridden by deterministic rules, not the LLM.
          </p>
        </div>
      )}

      {result.is_llm_fallback && (
        <div className="audit-section audit-section--fallback">
          <h4 className="audit-section-title">⚠️ LLM Fallback</h4>
          <p className="audit-note">
            LLM classification failed after maximum retries. Fallback result was used.
          </p>
        </div>
      )}
    </div>
  )
}
