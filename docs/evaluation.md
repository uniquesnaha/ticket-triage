# Evaluation report

Generated 2026-09-23 17:52 UTC with `openai/gpt-oss-120b` and prompt `triage@1.0.0#f85ae5e17157` by `python -m evals.run_eval` (from `backend/`).
Golden set: `backend/evals/golden.jsonl`, 24 cases. Wall time 22.2 s.

## Summary

| Metric | Result |
|---|---|
| Cases fully correct | 24/24 (100%) |
| `category` checks | 23/23 (100%) |
| `priority` checks | 19/19 (100%) |
| `needs_human_review` checks | 22/22 (100%) |
| `rules` checks | 13/13 (100%) |
| `customer_impact` checks | 1/1 (100%) |
| `sentiment` checks | 2/2 (100%) |
| `model_used` checks | 3/3 (100%) |
| `pii_redacted` checks | 1/1 (100%) |
| Human-review recall (should flag) | 14/14 (100%) |
| Human-review false alarms (should not flag) | 0/8 (0%) |
| Model not used (expected + unexpected) | 3 (0 unexpected) |
| Rationales withheld by output checks | 0 |
| Latency per ticket p50 / p95 | 860 ms / 3782 ms |

## Model alone vs model + rules

Accuracy of the raw model judgment compared with the final result after deterministic rules, on cases where the model ran.

| Field | Model alone | Model + rules |
|---|---|---|
| `category` | 20/20 (100%) | 20/20 (100%) |
| `priority` | 19/19 (100%) | 19/19 (100%) |
| `sentiment` | 2/2 (100%) | 2/2 (100%) |
| `customer_impact` | 1/1 (100%) | 1/1 (100%) |
| `needs_human_review` | 16/19 (84%) | 19/19 (100%) |

## Cases

| ID | Tags | Category | Priority | Review | Rules | Result |
|---|---|---|---|---|---|---|
| T001 | assessment | billing | high | yes | PAYMENT_ANOMALY | pass |
| T002 | assessment | auth | medium | no | - | pass |
| T003 | assessment | outage | critical | yes | OUTAGE_CRITICAL | pass |
| T004 | assessment, noise | feature_request | low | no | POSITIVE_SENTIMENT_GUARD | pass |
| T005 | assessment, noise | shipping | medium | no | - | pass |
| T006 | assessment, noise | billing | medium | yes | PAYMENT_ANOMALY | pass |
| T007 | assessment | bug | medium | no | - | pass |
| T008 | assessment | security | high | yes | SECURITY_REVIEW | pass |
| T009 | assessment, missing-info | unknown | low | yes | TRIVIAL_TICKET | pass |
| T010 | assessment | billing | low | no | NOT_URGENT | pass |
| X01 | injection | security | high | yes | INJECTION_FLAGGED | pass |
| X02 | injection, homoglyph | security | high | yes | INJECTION_FLAGGED | pass |
| X03 | pii | billing | medium | yes | PAYMENT_ANOMALY | pass |
| X04 | escalation | bug | high | yes | LEGAL_THREAT | pass |
| X05 | escalation, abuse | auth | medium | yes | ABUSIVE_LANGUAGE | pass |
| X06 | escalation, safety | security | critical | yes | SAFETY_ESCALATION | pass |
| X07 | missing-info | unknown | low | yes | MISSING_TEXT | pass |
| X08 | noise | outage | critical | yes | - | pass |
| X09 | noise | billing | low | no | - | pass |
| X10 | spam | spam | low | no | - | pass |
| X11 | mixed-signal | bug | low | no | POSITIVE_SENTIMENT_GUARD | pass |
| X12 | - | shipping | medium | no | - | pass |
| X13 | - | security | high | yes | - | pass |
| X14 | - | outage | critical | yes | - | pass |
