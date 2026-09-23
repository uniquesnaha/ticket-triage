// Mirrors the backend Pydantic schemas (backend/app/core/schema.py).

export type Category =
  | 'billing'
  | 'auth'
  | 'outage'
  | 'feature_request'
  | 'shipping'
  | 'security'
  | 'bug'
  | 'spam'
  | 'unknown'

export type Priority = 'critical' | 'high' | 'medium' | 'low'

export type Sentiment = 'positive' | 'neutral' | 'negative' | 'urgent'

export type CustomerImpact = 'all_customers' | 'multiple_customers' | 'single_customer' | 'none'

export type SecurityFlag =
  | 'injection_attempt'
  | 'excessive_length'
  | 'unicode_anomaly'
  | 'pii_redacted'

export type InputWarning =
  | 'missing_ticket_id'
  | 'missing_text'
  | 'duplicate_ticket_id'
  | 'text_truncated'

export interface ModelJudgment {
  category: Category
  priority: Priority
  sentiment: Sentiment
  customer_impact: CustomerImpact
  needs_human_review: boolean
  rationale: string
}

export interface FieldOverride {
  field: keyof Omit<ModelJudgment, 'rationale'>
  model_value: string | boolean
  final_value: string | boolean
  rule: string
}

export interface TriageResult {
  ticket_id: string
  original_text: string
  cleaned_text: string
  category: Category
  priority: Priority
  sentiment: Sentiment
  customer_impact: CustomerImpact
  needs_human_review: boolean
  rationale: string
  model_judgment: ModelJudgment | null
  field_overrides: FieldOverride[]
  guardrails_applied: string[]
  preprocessing_applied: string[]
  security_flags: SecurityFlag[]
  input_warnings: InputWarning[]
  llm_model: string
  prompt_version: string
  is_llm_fallback: boolean
  processing_time_ms: number
  processed_at: string
}

export interface TriageBatchResponse {
  results: TriageResult[]
  total: number
  processing_time_ms: number
  needs_human_review_count: number
  by_category: Record<string, number>
  by_priority: Record<string, number>
  model: string
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  environment: string
  model: string
  version: string
  llm_configured: boolean
  prompt_version: string
}

export interface RuleInfo {
  name: string
  description: string
  keywords: string[]
  condition: string | null
  sets: Record<string, string | boolean>
  max_priority: string | null
  min_priority: string | null
  corrects_sentiment_to: string | null
}
