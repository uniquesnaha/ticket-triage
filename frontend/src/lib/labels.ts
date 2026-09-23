import type {
  Category,
  CustomerImpact,
  InputWarning,
  Priority,
  SecurityFlag,
  Sentiment,
  TriageResult,
} from '../types/triage'

export const CATEGORY_LABEL: Record<Category, string> = {
  billing: 'Billing',
  auth: 'Login & access',
  outage: 'Outage',
  feature_request: 'Feature request',
  shipping: 'Shipping',
  security: 'Security',
  bug: 'Bug',
  spam: 'Spam',
  unknown: 'Unclassified',
}

export const PRIORITY_LABEL: Record<Priority, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

export const PRIORITIES: Priority[] = ['critical', 'high', 'medium', 'low']

export const PRIORITY_RANK: Record<Priority, number> = { critical: 4, high: 3, medium: 2, low: 1 }

export const SENTIMENT_LABEL: Record<Sentiment, string> = {
  urgent: 'Urgent',
  negative: 'Negative',
  neutral: 'Neutral',
  positive: 'Positive',
}

export const IMPACT_LABEL: Record<CustomerImpact, string> = {
  all_customers: 'All customers',
  multiple_customers: 'Several customers',
  single_customer: 'One customer',
  none: 'No impact',
}

export const FIELD_LABEL: Record<string, string> = {
  category: 'Category',
  priority: 'Priority',
  sentiment: 'Sentiment',
  customer_impact: 'Customer impact',
  needs_human_review: 'Human review',
}

export const RULE_LABEL: Record<string, string> = {
  OUTAGE_CRITICAL: 'Outage affecting many customers',
  SECURITY_REVIEW: 'Possible account compromise',
  PAYMENT_ANOMALY: 'Payment anomaly',
  NOT_URGENT: 'Customer said it is not urgent',
  POSITIVE_SENTIMENT_GUARD: 'Explicitly positive wording',
  TRIVIAL_TICKET: 'Too little text to classify',
  INJECTION_FLAGGED: 'Instructions aimed at the model',
  MISSING_TEXT: 'Ticket text is missing',
  OUTPUT_SAFETY_REVIEW: 'Model rationale failed checks',
}

export const PREPROCESS_LABEL: Record<string, string> = {
  UNICODE_NORMALIZE: 'Normalized unicode',
  STRIP_DEVICE_SIG: 'Removed device signature',
  STRIP_EMAIL_CLOSE: 'Removed email sign-off',
  DEDUP_FRAGMENTS: 'Removed repeated phrases',
  NORMALIZE_ALLCAPS: 'Converted all-caps text',
  COLLAPSE_WHITESPACE: 'Collapsed whitespace',
  FLAG_TRIVIAL: 'Flagged as very short',
}

export const SECURITY_LABEL: Record<SecurityFlag, string> = {
  injection_attempt: 'Prompt injection attempt',
  excessive_length: 'Text over length limit',
  unicode_anomaly: 'Look-alike characters',
}

export const WARNING_LABEL: Record<InputWarning, string> = {
  missing_ticket_id: 'Missing ticket ID (one was assigned)',
  missing_text: 'Missing ticket text',
  duplicate_ticket_id: 'Duplicate ticket ID in file',
  text_truncated: 'Text truncated to the length limit',
}

export function formatValue(field: string, value: string | boolean): string {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  switch (field) {
    case 'category':
      return CATEGORY_LABEL[value as Category] ?? value
    case 'priority':
      return PRIORITY_LABEL[value as Priority] ?? value
    case 'sentiment':
      return SENTIMENT_LABEL[value as Sentiment] ?? value
    case 'customer_impact':
      return IMPACT_LABEL[value as CustomerImpact] ?? value
    default:
      return value
  }
}

export type DecisionSource = 'model' | 'adjusted' | 'rules'

export function decisionSource(r: TriageResult): DecisionSource {
  if (r.is_llm_fallback) return 'rules'
  return r.field_overrides.length > 0 ? 'adjusted' : 'model'
}

export const SOURCE_LABEL: Record<DecisionSource, string> = {
  model: 'Model',
  adjusted: 'Model, adjusted',
  rules: 'Rules only',
}

/** Drop trailing machine markers like "[LLM_SKIPPED]"; they stay in the exported data. */
export function displayRationale(text: string): string {
  return text.replace(/\s*\[[A-Z_]+\]\s*$/, '')
}

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}
