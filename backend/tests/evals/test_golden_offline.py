"""Golden-set regression test that needs no model.

The model is stubbed with a bland answer, so only expectations owned by deterministic
code are checked here: which rules fire, when the model is skipped, and PII redaction.
The live model is scored separately by `python -m evals.run_eval`.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.schema import (
    Category,
    CustomerImpact,
    LLMTriageOutput,
    Priority,
    Sentiment,
    TicketInput,
)
from app.triage.pipeline import process_batch
from evals.run_eval import CaseScore, load_cases, score_case

DETERMINISTIC_CHECKS = {"rules", "model_used", "pii_redacted"}

BLAND = LLMTriageOutput(
    category=Category.UNKNOWN,
    priority=Priority.MEDIUM,
    sentiment=Sentiment.NEUTRAL,
    customer_impact=CustomerImpact.SINGLE_CUSTOMER,
    needs_human_review=False,
    rationale="Stub model answer for offline tests.",
)

CASES = load_cases()


def _run_with_stub(stub: AsyncMock) -> list[CaseScore]:
    tickets = [TicketInput(ticket_id=c.ticket_id, text=c.text) for c in CASES]
    with patch("app.triage.pipeline.classify_ticket", new=stub):
        results = asyncio.run(process_batch(tickets, "stub"))
    return [score_case(c, r) for c, r in zip(CASES, results, strict=True)]


@pytest.fixture(scope="module")
def scores() -> dict[str, CaseScore]:
    return {s.case.ticket_id: s for s in _run_with_stub(AsyncMock(return_value=(BLAND, False)))}


@pytest.mark.parametrize("ticket_id", [c.ticket_id for c in CASES])
def test_deterministic_expectations(ticket_id: str, scores: dict[str, CaseScore]) -> None:
    score = scores[ticket_id]
    failed = {k for k, ok in score.checks.items() if k in DETERMINISTIC_CHECKS and not ok}
    assert not failed, f"{ticket_id}: {failed} (rules fired: {score.result.guardrails_applied})"


def test_pii_never_reaches_model() -> None:
    stub = AsyncMock(return_value=(BLAND, False))
    _run_with_stub(stub)
    sent = [call.args[1] for call in stub.call_args_list]
    assert sent, "the model stub was never called"
    assert not any("@" in text or "4111" in text or "415 555" in text for text in sent)
