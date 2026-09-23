# Ticket Triage AI 🎫

> **Production-grade AI-powered support ticket triage** — FastAPI + LangChain + Groq (OpenAI-compatible LPU inference), with a React dashboard and multi-layer prompt injection defenses.

[![CI](https://github.com/your-org/ticket-triage/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/ticket-triage/actions)

---

## What It Does

Reads support tickets from a CSV file and returns a structured triage result for each:

| Field | Source | Description |
|---|---|---|
| `category` | LLM | billing, auth, outage, bug, security, shipping, feature_request, spam, unknown |
| `priority` | LLM + Guardrails | critical, high, medium, low |
| `sentiment` | LLM + Guardrails | urgent, negative, neutral, positive |
| `customer_impact` | LLM + Guardrails | all_customers, multiple_customers, single_customer, none |
| `needs_human_review` | LLM + Guardrails | boolean — true if human oversight required |
| `rationale` | LLM | 1-3 sentences citing evidence from the ticket text |
| `preprocessing_applied` | Deterministic | Transforms applied before LLM (audit trail) |
| `guardrails_applied` | Deterministic | Rule overrides applied after LLM (audit trail) |
| `security_flags` | Deterministic | Injection attempts, unicode anomalies detected |

---

## Architecture

```
CSV Upload
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI Backend                                      │
│                                                       │
│  CORS → TrustedHost → SecurityHeaders → RequestID    │
│  → RateLimit (slowapi) → X-API-Key auth              │
│                │                                      │
│  ┌─────────────▼────────────────────────────────┐   │
│  │ Triage Pipeline                               │   │
│  │                                               │   │
│  │  1. Input Security Scan                       │   │
│  │     - Injection pattern detection (27 regex)  │   │
│  │     - Unicode normalization (NFKC + homoglyphs│   │
│  │     - Length enforcement                      │   │
│  │                                               │   │
│  │  2. Text Preprocessor (deterministic)         │   │
│  │     - Dedup repeated fragments                │   │
│  │     - Strip device/email signatures           │   │
│  │     - Normalize ALL-CAPS sentences            │   │
│  │     - Flag trivial tickets                    │   │
│  │                                               │   │
│  │  3. LangChain + Groq (OpenAI-compatible)      │   │
│  │     - Sentinel delimiters in system prompt    │   │
│  │     - with_structured_output() (schema lock)  │   │
│  │     - tenacity retry (3x, exponential)        │   │
│  │     - Safe fallback on failure                │   │
│  │     [SKIPPED for high-risk injection tickets] │   │
│  │                                               │   │
│  │  4. Post-LLM Output Safety Scan               │   │
│  │     - Prompt leakage detection                │   │
│  │     - Hallucination pattern check             │   │
│  │     - Forbidden content filter                │   │
│  │                                               │   │
│  │  5. Deterministic Guardrail Engine            │   │
│  │     - 7 named rules override LLM output       │   │
│  │     - Each rule recorded in audit trail       │   │
│  └───────────────────────────────────────────────┘   │
│                │                                      │
│  TriageResult JSON (with full audit trail)            │
│  └─────────────────────────────────────────────────────┘
    │
    ▼
React Dashboard (Upload → Processing → Results Table → Detail Drawer)
```

---

## Quick Start (Docker Compose — Local Dev)

### 1. Prerequisites
- Docker + Docker Compose (or Python 3.12 + Node 20)
- Groq API key (free in 30 seconds at [console.groq.com/keys](https://console.groq.com/keys))

### 2. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
GROQ_API_KEY=gsk_your-free-groq-key-here
GROQ_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=llama-3.3-70b-versatile
TRIAGE_API_KEY=your-secret-key  # generate: python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start both services
```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| **React UI** | http://localhost:5173 |
| **FastAPI** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/api/v1/docs |

### 4. Upload tickets
Open the UI, drag and drop `project_1.csv`, and watch the triage run.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Groq API key (free at console.groq.com/keys) |
| `GROQ_BASE_URL` | — | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible base URL |
| `MODEL_NAME` | — | `llama-3.3-70b-versatile` | Model ID (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) |
| `TRIAGE_API_KEY` | ✅ | — | API key protecting triage endpoints |
| `ENVIRONMENT` | — | `development` | `development` or `production` |
| `LOG_LEVEL` | — | `INFO` | Logging level |
| `ALLOWED_ORIGINS` | — | `http://localhost:5173` | CORS origin allowlist (comma-separated) |
| `ALLOWED_HOSTS` | — | `localhost,127.0.0.1` | Trusted host allowlist |
| `MAX_TICKETS_PER_BATCH` | — | `50` | Maximum tickets per request |
| `MAX_TICKET_LENGTH` | — | `2000` | Max characters per ticket text |
| `TEMPERATURE` | — | `0.1` | LLM temperature (low = deterministic) |
| `MAX_RETRIES` | — | `3` | LLM retry attempts |

---

## API Reference

All endpoints are at `/api/v1/`. Auth: `X-API-Key: <your-key>` header.

### `POST /api/v1/triage`
Triage a batch of tickets (JSON).

```json
// Request
{
  "tickets": [
    { "ticket_id": "T001", "text": "I was charged twice for order 8841." }
  ]
}

// Response
{
  "results": [{ "ticket_id": "T001", "category": "billing", "priority": "high", ... }],
  "total": 1,
  "needs_human_review_count": 1,
  "by_category": { "billing": 1 },
  "by_priority": { "high": 1 },
  "model": "grok-beta",
  "processing_time_ms": 1240
}
```

### `POST /api/v1/triage/upload`
Upload a CSV file. Columns required: `ticket_id`, `text`.

### `GET /api/v1/health`
Public health check. Returns service status and model info.

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt

# All tests
pytest tests/ -v

# Security tests only
pytest tests/security/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Production Deployment (100% Free on Vercel)

The entire fullstack application (FastAPI backend serverless functions + React frontend) deploys directly to **[Vercel](https://vercel.com)** under a single domain.

### 1. Push to GitHub
```bash
git add .
git commit -m "feat: complete ticket triage production application for vercel"
git push -u origin main
```

### 2. Deploy on Vercel
1. Go to **[vercel.com](https://vercel.com)** and sign in.
2. Click **"Add New Project"** and import your repository.
3. In **Environment Variables**, add:
   - `GROQ_API_KEY`: *(your `gsk_...` key)*
   - `GROQ_BASE_URL`: `https://api.groq.com/openai/v1`
   - `MODEL_NAME`: `openai/gpt-oss-120b`
   - `TRIAGE_API_KEY`: `your-secret-triage-api-key-here`
   - `VITE_API_KEY`: `your-secret-triage-api-key-here`
4. Click **Deploy**.

Vercel automatically builds the Vite frontend, runs the FastAPI backend on serverless Python, and serves both under your production URL (e.g. `https://ticket-triage.vercel.app`).

---

## Security Design

### Prompt Injection Defenses (5 Layers)

1. **Pre-LLM regex scanner** — 27 injection patterns detected. High-risk tickets never reach the LLM.
2. **Unicode normalization** — NFKC normalization neutralizes homoglyph attacks.
3. **Sentinel delimiters** — User content wrapped in `<<<TICKET_START>>>...<<<TICKET_END>>>` in system prompt.
4. **Structured output schema** — LLM constrained to JSON fields via function calling. Cannot produce free-form instructions.
5. **Post-LLM output scan** — Rationale checked for prompt leakage, hallucinations, and forbidden content.

### Other Security Controls

- **`X-API-Key` auth** — timing-safe `hmac.compare_digest` comparison
- **Rate limiting** — 30 req/min (triage), 5 req/min (upload) per IP via slowapi
- **CORS** — explicit origin allowlist, no wildcard
- **TrustedHostMiddleware** — prevents Host header attacks
- **Input validation** — max 50 tickets, 2000 chars each, 5MB file max
- **Security headers** — `X-Frame-Options`, `X-Content-Type-Options`, `CSP`, `Referrer-Policy`
- **No hardcoded secrets** — all credentials via environment variables
- **PII-safe logging** — ticket text truncated in logs, no credentials ever logged
- **API docs disabled in production**

---

## Design Decisions

### LLM vs. Deterministic Rules

The system clearly separates **model judgment** from **deterministic rules**:

- **LLM** handles nuanced classification that requires language understanding (category inference, sentiment, rationale generation)
- **Guardrails** enforce explicit evidence — if a ticket says "Production is down for every customer", we **know** it's CRITICAL regardless of what the LLM says
- Every overridden field is tracked in `guardrails_applied` so evaluators can see exactly what changed

### Why Low Temperature (0.1)?

Classification tasks benefit from determinism. With temperature=0.1, the model picks the most confident answer rather than sampling from the distribution.

### Why tenacity with exponential backoff?

Groq API calls can fail transiently (rate limits, network hiccups). Rather than immediately returning an error, we retry up to 3 times with increasing waits (2s → 4s → 8s). If all retries fail, we return a safe fallback result with `needs_human_review=True` — the batch still completes, just that ticket gets flagged.

---

## Project Structure

```
ticket-triage/
├── backend/app/
│   ├── core/           — Config, schemas, exceptions, logging
│   ├── security/       — Injection scanner, output validator, auth
│   ├── triage/         — Preprocessor, LLM chain, guardrails, pipeline
│   ├── api/v1/         — FastAPI routes
│   └── middleware/     — Request ID, security headers
├── frontend/src/
│   ├── components/     — UI components
│   ├── hooks/          — useTriage state machine
│   ├── api/            — Axios client
│   └── types/          — TypeScript types
├── tests/              — pytest test suite
├── api/index.py        — Vercel Serverless Function entrypoint
├── vercel.json         — Vercel Fullstack routing configuration
└── .github/workflows/  — CI/CD
```
