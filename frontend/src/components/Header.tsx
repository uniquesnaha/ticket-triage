import { Zap } from 'lucide-react'

export function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-logo">
          <div className="logo-icon">
            <Zap size={22} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="logo-title">Ticket Triage AI</h1>
            <p className="logo-subtitle">Powered by Groq · LangChain · Deterministic Guardrails</p>
          </div>
        </div>
        <div className="header-badges">
          <span className="env-badge">v1.0</span>
          <span className="env-badge env-badge-security">🔒 Prompt Injection Protected</span>
        </div>
      </div>
    </header>
  )
}
