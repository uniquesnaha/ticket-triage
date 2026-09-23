import { useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  CATEGORY_LABEL,
  FIELD_LABEL,
  IMPACT_LABEL,
  PRIORITY_LABEL,
  RULE_LABEL,
  SENTIMENT_LABEL,
  formatValue,
} from '../lib/labels'
import type { RuleInfo } from '../types/triage'

const PIPELINE: { name: string; text: string }[] = [
  {
    name: 'Screen',
    text: 'Look-alike characters are normalized and the text is checked for instructions aimed at the model. Suspicious tickets skip the model entirely.',
  },
  {
    name: 'Protect',
    text: 'Emails, phone numbers, card numbers, bank accounts and API keys are replaced with placeholders such as [EMAIL]. The model never sees them. Abuse, legal threats and self-harm are detected here too.',
  },
  {
    name: 'Clean',
    text: 'Device signatures, email sign-offs and repeated phrases are removed, and all-caps text is converted, so the model sees the actual request.',
  },
  {
    name: 'Classify',
    text: 'The model fills a fixed schema. Malformed answers and provider errors are retried; if it still fails, the ticket goes to human review.',
  },
  {
    name: 'Check the answer',
    text: 'Quotes and numbers in the rationale must appear in the ticket. A rationale that invents facts or leaks instructions is withheld.',
  },
  {
    name: 'Apply rules',
    text: 'Explicit evidence in the ticket overrides the model. Every change is recorded next to what the model originally said.',
  },
]

const FIELDS: { field: string; values: string; source: string }[] = [
  { field: 'Category', values: Object.values(CATEGORY_LABEL).join(', '), source: 'Model, rules can override' },
  { field: 'Priority', values: Object.values(PRIORITY_LABEL).join(', '), source: 'Model, rules can override' },
  { field: 'Sentiment', values: Object.values(SENTIMENT_LABEL).join(', '), source: 'Model, rules can override' },
  { field: 'Customer impact', values: Object.values(IMPACT_LABEL).join(', '), source: 'Model, rules can override' },
  { field: 'Human review', values: 'Yes, No', source: 'Model, rules can only turn it on' },
  { field: 'Rationale', values: '1 to 3 sentences quoting the ticket', source: 'Model, checked before use' },
]

function ruleTrigger(rule: RuleInfo): string {
  if (rule.condition) return rule.condition
  const shown = rule.keywords.slice(0, 3).map((k) => `"${k}"`)
  const more = rule.keywords.length - shown.length
  return `Text contains ${shown.join(', ')}${more > 0 ? ` or ${more} similar phrases` : ''}`
}

function ruleEffects(rule: RuleInfo): string[] {
  const effects = Object.entries(rule.sets)
    .filter(([field]) => field !== 'needs_human_review')
    .map(([field, value]) => `${FIELD_LABEL[field] ?? field}: ${formatValue(field, value)}`)
  if (rule.max_priority) effects.push(`Priority capped at ${formatValue('priority', rule.max_priority)}`)
  if (rule.min_priority) effects.push(`Priority at least ${formatValue('priority', rule.min_priority)}`)
  if (rule.corrects_sentiment_to) {
    effects.push(
      `Negative or urgent sentiment becomes ${formatValue('sentiment', rule.corrects_sentiment_to)}`,
    )
  }
  if (rule.sets.needs_human_review) effects.push('Flags for human review')
  return effects
}

export function HowItWorksPage() {
  const [rules, setRules] = useState<RuleInfo[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    api.rules().then(setRules, () => setError(true))
  }, [])

  return (
    <div className="page page--narrow page--doc">
      <header className="page-header">
        <h1>How it works</h1>
        <p className="page-desc">
          Every ticket gets a model judgment, then deterministic rules check it against what the
          ticket actually says. The two are never blended silently: each result shows what the
          model said and which rule changed it.
        </p>
      </header>

      <section className="doc-section">
        <h2>Pipeline</h2>
        <ol className="pipeline">
          {PIPELINE.map((step) => (
            <li key={step.name}>
              <h3>{step.name}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="doc-section">
        <h2>Output fields</h2>
        <div className="table-scroll">
          <table className="table table--doc">
            <thead>
              <tr>
                <th>Field</th>
                <th>Possible values</th>
                <th>Decided by</th>
              </tr>
            </thead>
            <tbody>
              {FIELDS.map((f) => (
                <tr key={f.field}>
                  <td className="cell-strong">{f.field}</td>
                  <td className="cell-wrap">{f.values}</td>
                  <td className="cell-wrap muted">{f.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="doc-section">
        <h2>Rules</h2>
        <p className="doc-lede">Loaded from the running server, so this list is always current.</p>
        {error && <p className="inline-error">Could not load the rules from the server.</p>}
        {!rules && !error && <div className="composer-pending"><span className="skeleton-line" /></div>}
        {rules && (
          <div className="table-scroll">
            <table className="table table--doc">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Fires when</th>
                  <th>Effect</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.name}>
                    <td className="cell-wrap">
                      <span className="cell-strong">{RULE_LABEL[rule.name] ?? rule.name}</span>
                      <code className="rule-code">{rule.name}</code>
                    </td>
                    <td className="cell-wrap">{ruleTrigger(rule)}</td>
                    <td className="cell-wrap">
                      <ul className="effects">
                        {ruleEffects(rule).map((effect) => (
                          <li key={effect}>{effect}</li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="doc-section">
        <h2>When the model is not used</h2>
        <p className="doc-lede">
          These tickets get a safe default and are always flagged for human review. The result
          says why, and the run summary counts them under &ldquo;Model not used&rdquo;.
        </p>
        <ul className="plain-list">
          <li>The ticket text is empty.</li>
          <li>The text contains instructions aimed at the model.</li>
          <li>The model failed to return a valid answer after every retry.</li>
          <li>The batch ran out of time before the ticket was classified.</li>
        </ul>
      </section>
    </div>
  )
}
