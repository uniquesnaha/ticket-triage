"""Evaluate the triage pipeline against a labelled golden set.

    python -m evals.run_eval                      # real model, writes ../docs/evaluation.md
    python -m evals.run_eval --report out.md --json out.json

Each golden case lists only the expectations that are unambiguous. Where reasonable
triagers could disagree (e.g. medium vs high), the case accepts a set of values.

Besides final accuracy, the report compares the raw model judgment with the final result,
which shows what the deterministic rules add on top of the model.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.schema import TicketInput, TriageResult
from app.triage.llm import get_prompt
from app.triage.pipeline import process_batch

GOLDEN_PATH = Path(__file__).with_name("golden.jsonl")
DEFAULT_REPORT = Path(__file__).resolve().parents[2] / "docs" / "evaluation.md"

LABEL_FIELDS = ("category", "priority", "sentiment", "customer_impact")


@dataclass
class Case:
    ticket_id: str
    text: str
    expect: dict[str, Any]
    tags: list[str] = field(default_factory=list)


@dataclass
class CaseScore:
    case: Case
    result: TriageResult
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def load_cases(path: Path = GOLDEN_PATH) -> list[Case]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Case(**json.loads(line)) for line in lines if line.strip()]


def _value(result: TriageResult | Any, name: str) -> str:
    return str(getattr(result, name))


def score_case(case: Case, result: TriageResult) -> CaseScore:
    expect = case.expect
    checks: dict[str, bool] = {}
    for name in LABEL_FIELDS:
        if name in expect:
            checks[name] = _value(result, name) in expect[name]
    if "needs_human_review" in expect:
        checks["needs_human_review"] = result.needs_human_review == expect["needs_human_review"]
    if "rules" in expect:
        checks["rules"] = set(expect["rules"]) <= set(result.guardrails_applied)
    if "model_used" in expect:
        checks["model_used"] = (not result.is_llm_fallback) == expect["model_used"]
    if "pii_redacted" in expect:
        redacted = {t.removeprefix("REDACT_") for t in result.preprocessing_applied}
        checks["pii_redacted"] = set(expect["pii_redacted"]) <= redacted
    return CaseScore(case=case, result=result, checks=checks)


def _rate(hits: int, total: int) -> str:
    return f"{hits}/{total} ({hits / total:.0%})" if total else "n/a"


def summarise(scores: list[CaseScore]) -> dict[str, Any]:
    per_check: dict[str, list[bool]] = {}
    for s in scores:
        for name, ok in s.checks.items():
            per_check.setdefault(name, []).append(ok)

    # Model-only vs final accuracy on label fields (cases where the model ran).
    model_vs_final: dict[str, dict[str, int]] = {}
    for name in (*LABEL_FIELDS, "needs_human_review"):
        model_hits = final_hits = total = 0
        for s in scores:
            judgment = s.result.model_judgment
            if name not in s.case.expect or judgment is None:
                continue
            total += 1
            expected = s.case.expect[name]
            if name == "needs_human_review":
                model_hits += judgment.needs_human_review == expected
                final_hits += s.result.needs_human_review == expected
            else:
                model_hits += _value(judgment, name) in expected
                final_hits += _value(s.result, name) in expected
        if total:
            model_vs_final[name] = {"model": model_hits, "final": final_hits, "total": total}

    should_review = [s for s in scores if s.case.expect.get("needs_human_review") is True]
    should_not = [s for s in scores if s.case.expect.get("needs_human_review") is False]
    latencies = [s.result.processing_time_ms for s in scores if not s.result.is_llm_fallback]

    return {
        "cases": len(scores),
        "cases_passed": sum(s.passed for s in scores),
        "checks": {k: {"passed": sum(v), "total": len(v)} for k, v in per_check.items()},
        "model_vs_final": model_vs_final,
        "review_recall": {
            "flagged": sum(s.result.needs_human_review for s in should_review),
            "total": len(should_review),
        },
        "review_false_alarms": {
            "flagged": sum(s.result.needs_human_review for s in should_not),
            "total": len(should_not),
        },
        "model_not_used": sum(s.result.is_llm_fallback for s in scores),
        "unexpected_fallbacks": sum(
            s.result.is_llm_fallback and s.case.expect.get("model_used", True) for s in scores
        ),
        "rationales_withheld": sum(
            "OUTPUT_SAFETY_REVIEW" in s.result.guardrails_applied for s in scores
        ),
        "rules_fired": dict(Counter(r for s in scores for r in s.result.guardrails_applied)),
        "latency_ms": {
            "p50": int(statistics.median(latencies)) if latencies else None,
            "p95": int(sorted(latencies)[max(0, round(len(latencies) * 0.95) - 1)])
            if latencies
            else None,
        },
    }


def render_report(
    summary: dict[str, Any], scores: list[CaseScore], model: str, elapsed: float
) -> str:
    lines = [
        "# Evaluation report",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC with `{model}` and prompt "
        f"`{get_prompt().ref}` by `python -m evals.run_eval` (from `backend/`).",
        f"Golden set: `backend/evals/golden.jsonl`, {summary['cases']} cases. "
        f"Wall time {elapsed:.1f} s.",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Cases fully correct | {_rate(summary['cases_passed'], summary['cases'])} |",
    ]
    for name, c in summary["checks"].items():
        lines.append(f"| `{name}` checks | {_rate(c['passed'], c['total'])} |")
    rr, fa = summary["review_recall"], summary["review_false_alarms"]
    lines += [
        f"| Human-review recall (should flag) | {_rate(rr['flagged'], rr['total'])} |",
        f"| Human-review false alarms (should not flag) | {_rate(fa['flagged'], fa['total'])} |",
        f"| Model not used (expected + unexpected) | {summary['model_not_used']} "
        f"({summary['unexpected_fallbacks']} unexpected) |",
        f"| Rationales withheld by output checks | {summary['rationales_withheld']} |",
        f"| Latency per ticket p50 / p95 | {summary['latency_ms']['p50']} ms / "
        f"{summary['latency_ms']['p95']} ms |",
        "",
        "## Model alone vs model + rules",
        "",
        "Accuracy of the raw model judgment compared with the final result after deterministic "
        "rules, on cases where the model ran.",
        "",
        "| Field | Model alone | Model + rules |",
        "|---|---|---|",
    ]
    for name, m in summary["model_vs_final"].items():
        lines.append(
            f"| `{name}` | {_rate(m['model'], m['total'])} | {_rate(m['final'], m['total'])} |"
        )
    lines += [
        "",
        "## Cases",
        "",
        "| ID | Tags | Category | Priority | Review | Rules | Result |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in scores:
        r = s.result
        failed = [k for k, ok in s.checks.items() if not ok]
        lines.append(
            f"| {s.case.ticket_id} | {', '.join(s.case.tags) or '-'} | {r.category} | {r.priority} "
            f"| {'yes' if r.needs_human_review else 'no'} "
            f"| {', '.join(r.guardrails_applied) or '-'} "
            f"| {'pass' if not failed else 'FAIL: ' + ', '.join(failed)} |"
        )
    return "\n".join(lines) + "\n"


async def run(cases: list[Case]) -> tuple[list[CaseScore], float]:
    start = time.monotonic()
    tickets = [TicketInput(ticket_id=c.ticket_id, text=c.text) for c in cases]
    results = await process_batch(tickets, get_settings().model_name)
    return [score_case(c, r) for c, r in zip(cases, results, strict=True)], time.monotonic() - start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.run_eval")
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", type=Path, help="Also write raw results + summary as JSON")
    args = parser.parse_args(argv)

    configure_logging(stream=sys.stderr)
    settings = get_settings()
    if not settings.llm_configured:
        print(
            "error: GROQ_API_KEY is not set; an evaluation needs the real model.", file=sys.stderr
        )
        return 2

    cases = load_cases(args.golden)
    scores, elapsed = asyncio.run(run(cases))
    summary = summarise(scores)
    args.report.write_text(
        render_report(summary, scores, settings.model_name, elapsed), encoding="utf-8", newline="\n"
    )
    if args.json:
        payload = {
            "summary": summary,
            "results": [s.result.model_dump(mode="json") for s in scores],
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")

    print(
        f"{summary['cases_passed']}/{summary['cases']} cases fully correct. Report: {args.report}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
