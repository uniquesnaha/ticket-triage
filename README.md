# Ticket Triage

Support-ticket triage with **schema-enforced LLM output** and **deterministic guardrails**.
Each ticket in a CSV becomes one JSON object with `category`, `priority`, `sentiment`,
`customer_impact`, `needs_human_review`, and a `rationale` grounded in the ticket text,
plus a provenance trail showing exactly what the model decided and what rules changed.

- **CLI** — `python -m app.cli data/project_1.csv` → JSON Lines, one object per input row
- **API** — FastAPI (`/api/v1/triage`, `/api/v1/triage/upload`)
- **UI** — React workspace: upload a CSV, filter the queue, open any ticket to see the model's call next to each rule override
- **Deploy** — one Vercel project: static frontend + Python serverless function

The original assignment is in [docs/guidelines.md](docs/guidelines.md); the input data is
[data/project_1.csv](data/project_1.csv).

---

## How a ticket is processed

```
CSV row
  │  csv_loader     missing ticket_id → ROW-n, missing text / duplicates / over-length → input_warnings
  ▼
input_guard         NFKC + homoglyph normalisation, prompt-injection patterns (high risk → skip LLM)
  ▼
preprocessor        strip device signatures & sign-offs, dedupe repeated fragments,
  │                 normalise ALL-CAPS, collapse whitespace, flag trivial tickets
  ▼
LLM (LangChain → Groq, OpenAI-compatible)
  │                 tool-calling bound to a Pydantic schema (LLMTriageOutput)
  │                 retries: malformed/invalid output, 429 (honours Retry-After), 5xx, timeouts
  │                 after MAX_RETRIES → deterministic safe fallback (needs_human_review = true)
  ▼
output_guard        rationale must not leak the prompt, contain forbidden content, or cite
  │                 quotes/numbers that are not in the ticket → otherwise withheld + escalated
  ▼
guardrails          named rules override fields when the ticket contains explicit evidence
  ▼
TriageResult        final fields + model_judgment + field_overrides + audit lists
```

### Model judgment vs deterministic rules

The two are never blended silently:

| Field | Meaning |
|---|---|
| `model_judgment` | The validated model output *before* rules (`null` if the model was not used). |
| `field_overrides` | Every field a rule changed: `{field, model_value, final_value, rule}`. |
| `guardrails_applied` | Every rule that matched, including ones that agreed with the model. |
| `rationale` | The model's rationale (never edited by rules). If the model was not used, or its rationale failed validation, a system message says why. |
| `is_llm_fallback` | `true` when the result is a deterministic safe default, not a model judgment. |
| `preprocessing_applied`, `security_flags`, `input_warnings` | What was cleaned, detected, or missing. |

Guardrail rules (see [backend/app/triage/guardrails.py](backend/app/triage/guardrails.py)):

| Rule | Trigger | Effect |
|---|---|---|
| `OUTAGE_CRITICAL` | "production is down", "every customer", … | priority → critical, impact → all_customers, review |
| `SECURITY_REVIEW` | "may have accessed", "unauthorized access", … | category → security, priority → high, review |
| `PAYMENT_ANOMALY` | "charged twice", "payment failed", … | category → billing, review |
| `NOT_URGENT` | "not urgent", "no rush", … | priority capped at medium |
| `POSITIVE_SENTIMENT_GUARD` | "love the", "awesome", … | negative/urgent sentiment → positive |
| `TRIVIAL_TICKET` | ≤ 2 words and no evidence rule fired | category → unknown, priority → low, review |
| `INJECTION_FLAGGED` | high-risk injection pattern (LLM skipped) | category → security, priority → high, review |
| `MISSING_TEXT` | blank ticket text (LLM skipped) | unknown / low / none, review |
| `OUTPUT_SAFETY_REVIEW` | model rationale failed validation | review |

Rules may only *escalate* `needs_human_review`, never clear it.

---

## Quick start (local)

Prerequisites: Python 3.12, Node 20+, a free Groq API key from <https://console.groq.com/keys>.

```bash
cp .env.example .env          # set GROQ_API_KEY
```

### CLI — the assignment deliverable

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python -m app.cli ../data/project_1.csv                      # JSONL to stdout
python -m app.cli ../data/project_1.csv -o results.jsonl     # to a file
python -m app.cli ../data/project_1.csv --format json        # single JSON array
```

Logs go to stderr, so stdout is always valid JSON Lines. Exit code `2` means the input
file is unreadable or not a ticket CSV.

### API + UI

```bash
# terminal 1
cd backend && uvicorn app.main:app --reload            # http://localhost:8000/api/v1/docs

# terminal 2
cd frontend && npm ci && npm run dev                   # http://localhost:5173
```

Open the UI and click **Try the sample**. Or run both with `docker compose up --build`.

---

## Deploying to Vercel

The repo is a single Vercel project: `vercel.json` builds `frontend/` to static files and
deploys `api/index.py` (which imports `backend/app`) as a Python serverless function.
`/api/*` is routed to the function and everything else to the SPA.

1. **Push to GitHub** (or GitLab/Bitbucket).
2. **Import the repo** at <https://vercel.com/new>. Leave *Root Directory* as the repo root
   and *Framework Preset* as **Other**. `vercel.json` already defines the install, build,
   and output settings, so don't override them.
3. **Add environment variables** (Project → Settings → Environment Variables, for
   *Production* and *Preview*):

   | Name | Value |
   |---|---|
   | `GROQ_API_KEY` | your `gsk_…` key |
   | `ENVIRONMENT` | `production` |
   | `MODEL_NAME` | *(optional)* default `openai/gpt-oss-120b` |
   | `ALLOWED_HOSTS` | *(only for a custom domain)* e.g. `triage.example.com` |

   Don't set `TRIAGE_API_KEY` for a public UI deployment (see [Access control](#access-control)),
   and never put secrets in `VITE_*` variables: they are compiled into the public bundle.
4. **Deploy.** When it finishes, open `https://<project>.vercel.app/api/v1/health` and
   check that it shows `"status": "ok"` and `"llm_configured": true`.
5. Open the site and click **Try the sample**, or upload your own CSV.

Vercel-specific notes:

- The function's `maxDuration` is 60 s (`vercel.json`), and `BATCH_TIMEOUT` (50 s) keeps the
  API under that: tickets still unfinished at the deadline come back as needs-review fallbacks
  instead of the request failing with a 504.
- Vercel limits request bodies to 4.5 MB, so `MAX_CSV_SIZE_MB` defaults to 4.
- Hosts are validated. The deployment's own `*.vercel.app` URLs are trusted automatically
  (via Vercel's system env vars); list custom domains in `ALLOWED_HOSTS`.
- Changing an environment variable only takes effect after a **redeploy**.

---

## Configuration

All settings are environment variables (see [.env.example](.env.example)). The main ones:

| Variable | Default | Notes |
|---|---|---|
| `GROQ_API_KEY` | — | Required for real classification; without it `/health` reports `degraded`. |
| `TRIAGE_API_KEY` | unset | Optional. When set, triage calls need `X-API-Key` (disables browser use). |
| `MODEL_NAME` | `openai/gpt-oss-120b` | Any Groq model with tool calling. |
| `LLM_REASONING_EFFORT` | auto | `low` for gpt-oss models; `none` to disable. |
| `MAX_RETRIES` | `4` | Total LLM attempts per ticket. |
| `LLM_CONCURRENCY` | `4` | Parallel LLM calls per batch. |
| `BATCH_TIMEOUT` | `50` | Seconds (API only; the CLI waits for every ticket). |
| `MAX_TICKETS_PER_BATCH` | `50` | API limit per request. |
| `ENVIRONMENT` | `development` | `production` = JSON logs, API docs disabled. |

---

## API

All endpoints are under `/api/v1`. Triage endpoints require `X-API-Key` only when
`TRIAGE_API_KEY` is set. Errors use RFC 7807 `application/problem+json`.

| Method | Path | Body |
|---|---|---|
| `GET` | `/health` | — (public) |
| `POST` | `/triage` | `{"tickets": [{"ticket_id": "T001", "text": "…"}]}` |
| `POST` | `/triage/upload` | multipart `file` = CSV with `ticket_id,text` columns |

Both triage endpoints return `{results: TriageResult[], total, needs_human_review_count,
by_category, by_priority, model, processing_time_ms}`, with results in input order.

---

## Development

```bash
cd backend
ruff check app tests && ruff format --check app tests
mypy app                       # strict
pytest --cov=app

cd ../frontend
npm run lint && npm run build
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all of the above on every
push and PR. Tests never call the real LLM.

### Project structure

```
├── api/index.py              Vercel serverless entrypoint (imports backend/app)
├── backend/
│   ├── app/
│   │   ├── cli.py            CSV → JSONL command-line tool
│   │   ├── main.py           FastAPI app factory
│   │   ├── api/v1/           HTTP routes
│   │   ├── core/             config, schemas, errors, logging, rate limiting
│   │   ├── middleware/       request ID, security headers
│   │   ├── security/         auth, input (injection) guard, output (rationale) guard
│   │   └── triage/           csv_loader, preprocessor, llm, guardrails, pipeline
│   ├── tests/
│   ├── requirements-dev.txt  test/lint tools (+ ../requirements.txt)
│   └── Dockerfile            production image (build from repo root)
├── frontend/                 React + Vite + TypeScript
├── data/project_1.csv        assignment input
├── docs/guidelines.md        assignment brief
├── requirements.txt          runtime Python deps (Vercel, Docker, dev)
└── vercel.json
```

---

## Security

- **No secrets in code or the bundle.** The Groq key lives only in server environment variables.
- **Prompt injection:** pattern scan before the LLM (high-risk tickets never reach it),
  sentinel-delimited untrusted input, schema-bound tool output, post-LLM rationale checks.
- **HTTP:** trusted-host allowlist, strict CORS, CSP and security headers on API and static
  responses, request IDs validated before being echoed.
- **Limits:** batch size, text length, upload size, and per-IP rate limits.
- **Logging:** structured JSON in production; ticket text and error payloads are truncated.
- **CSV export** in the UI neutralises spreadsheet formula injection.

## Access control

The web UI has no login. Anyone with the URL can triage up to 50 tickets per request. That
is deliberate for a demo, and the exposure is small:

- The Groq key never leaves the server. The worst an outsider can do is use up the free-tier
  quota, which costs nothing and resets every minute or day.
- Per-IP rate limits (20 JSON / 6 upload requests a minute), batch and size caps, and
  prompt-injection screening all still apply.

When that stops being acceptable (real customer data, a paid LLM account), add real access
control rather than a shared key typed into the browser:

- **Vercel Deployment Protection** (Vercel login or password) in front of the whole site, or
- SSO/OAuth at the edge (e.g. Auth.js, Clerk).

`TRIAGE_API_KEY` remains for **API-only** use (scripts, other services calling
`/api/v1/triage`); when it is set, the browser UI cannot call the API.

## Known limitations

- **Groq free-tier limits.** `openai/gpt-oss-120b` has a low tokens-per-minute quota on the
  free tier, so a 10-ticket batch can hit 429s. The client honours `Retry-After`, and
  tickets that still fail fall back to needs-review. For steady throughput, use a paid Groq
  tier or lower `LLM_CONCURRENCY`.
- **Rate limits are per instance** (in memory). On serverless each warm instance counts
  separately; use a Redis-backed limiter for a global quota.
- **No user accounts.** See [Access control](#access-control).
