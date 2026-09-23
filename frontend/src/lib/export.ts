import type { TriageResult } from '../types/triage'

function save(content: string, type: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function baseName(sourceFile: string) {
  return sourceFile.replace(/\.[^.]+$/, '') || 'tickets'
}

export function exportJSONL(results: TriageResult[], sourceFile: string) {
  const body = results.map((r) => JSON.stringify(r)).join('\n') + '\n'
  save(body, 'application/x-ndjson', `${baseName(sourceFile)}.triaged.jsonl`)
}

// RFC 4180 quoting, plus neutralising leading =,+,-,@ so spreadsheet apps don't
// execute ticket text as a formula (CSV injection).
function cell(value: unknown): string {
  let text = String(value)
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

const COLUMNS: [string, (r: TriageResult) => unknown][] = [
  ['ticket_id', (r) => r.ticket_id],
  ['category', (r) => r.category],
  ['priority', (r) => r.priority],
  ['sentiment', (r) => r.sentiment],
  ['customer_impact', (r) => r.customer_impact],
  ['needs_human_review', (r) => r.needs_human_review],
  ['rationale', (r) => r.rationale],
  ['rules_applied', (r) => r.guardrails_applied.join('|')],
  ['fields_overridden', (r) => r.field_overrides.map((o) => o.field).join('|')],
  ['model_used', (r) => !r.is_llm_fallback],
  ['input_warnings', (r) => r.input_warnings.join('|')],
  ['security_flags', (r) => r.security_flags.join('|')],
  ['text', (r) => r.original_text],
]

export function exportCSV(results: TriageResult[], sourceFile: string) {
  const header = COLUMNS.map(([name]) => name).join(',')
  const rows = results.map((r) => COLUMNS.map(([, get]) => cell(get(r))).join(','))
  save([header, ...rows].join('\r\n'), 'text/csv', `${baseName(sourceFile)}.triaged.csv`)
}
