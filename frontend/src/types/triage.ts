// All TypeScript types matching the backend Pydantic schemas

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

export type CustomerImpact =
  | 'all_customers'
  | 'multiple_customers'
  | 'single_customer'
  | 'none'

export type SecurityFlag = 'injection_attempt' | 'excessive_length' | 'unicode_anomaly'

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
  field: string
  model_value: string | boolean
  final_value: string | boolean
  rule: string
}

export interface TicketInput {
  ticket_id: string
  text: string
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

export interface TriageBatchRequest {
  tickets: TicketInput[]
}

// UI-specific derived types
export type TriageFilter = {
  category: Category | 'all'
  priority: Priority | 'all'
  needsReview: boolean | null
}
