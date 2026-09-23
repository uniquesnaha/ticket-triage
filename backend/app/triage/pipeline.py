"""Triage pipeline — orchestrates preprocessing → LLM → output guard → guardrails."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence

import structlog

from app.core.config import get_settings
from app.core.schema import (
    InputWarning,
    LLMTriageOutput,
    SecurityFlag,
    TicketInput,
    TriageResult,
)
from app.security.content_signals import detect_content_signals
from app.security.input_guard import RiskLevel, scan_for_injection
from app.security.output_guard import validate_output
from app.security.pii import redact_pii
from app.triage.guardrails import apply_guardrails
from app.triage.llm import (
    ERROR_RESULT,
    INJECTION_SKIPPED_RESULT,
    MISSING_TEXT_RESULT,
    TIMEOUT_RESULT,
    classify_ticket,
    get_prompt,
)
from app.triage.preprocessor import preprocess

logger = structlog.get_logger()

_SCAN_FLAGS = {
    "unicode_anomaly": SecurityFlag.UNICODE_ANOMALY,
    "excessive_length": SecurityFlag.EXCESSIVE_LENGTH,
}


async def process_ticket(
    ticket: TicketInput,
    model_name: str,
    input_warnings: Sequence[InputWarning] = (),
) -> TriageResult:
    """
    Full triage pipeline for a single ticket.

      1. Input security scan (injection detection, unicode normalisation, length) and
         content signals (abuse, legal threats, safety risk)
      2. PII redaction, then text preprocessing (deterministic cleaning)
      3. LLM classification (skipped for missing text and high-risk injections)
      4. Post-LLM output validation (leakage, forbidden content, unsupported evidence)
      5. Deterministic guardrails (recorded as field overrides)
      6. Assemble the final TriageResult with its provenance trail
    """
    start = time.monotonic()
    warnings = list(input_warnings)
    security_flags: list[SecurityFlag] = []
    log = logger.bind(ticket_id=ticket.ticket_id)
    log.info("pipeline_start", text_length=len(ticket.text))

    missing_text = not ticket.text.strip()
    if missing_text and InputWarning.MISSING_TEXT not in warnings:
        warnings.append(InputWarning.MISSING_TEXT)

    # ── Step 1: Input security scan ───────────────────────────────────────────
    scan = scan_for_injection(ticket.text, max_length=get_settings().max_ticket_length)
    security_flags.extend(_SCAN_FLAGS[f] for f in scan.security_flags if f in _SCAN_FLAGS)
    injection_flagged_high = scan.risk_level == RiskLevel.HIGH
    if injection_flagged_high:
        security_flags.append(SecurityFlag.INJECTION_ATTEMPT)
        log.warning("injection_detected", matched_patterns=scan.matched_patterns)

    normalized = scan.normalized_text or ticket.text
    signals = detect_content_signals(normalized)

    # ── Step 2: PII redaction + preprocessing ─────────────────────────────────
    # The model never needs contact or payment details to classify a ticket.
    redaction = redact_pii(normalized)
    if redaction.found:
        security_flags.append(SecurityFlag.PII_REDACTED)
    prep = preprocess(redaction.text)
    prep.transforms_applied[:0] = [f"REDACT_{label}" for label in redaction.found]

    # ── Step 3: LLM classification ────────────────────────────────────────────
    model_judgment: LLMTriageOutput | None = None
    if missing_text:
        llm_output, is_llm_fallback = MISSING_TEXT_RESULT, True
    elif injection_flagged_high:
        log.warning("llm_skipped_injection")
        llm_output, is_llm_fallback = INJECTION_SKIPPED_RESULT, True
    else:
        llm_output, is_llm_fallback = await classify_ticket(ticket.ticket_id, prep.cleaned_text)

    # ── Step 4: Post-LLM output validation (model output only) ────────────────
    output_flagged = False
    if not is_llm_fallback:
        output_scan = validate_output(llm_output.rationale, [ticket.text, prep.cleaned_text])
        if not output_scan.is_safe:
            output_flagged = True
            log.warning("output_safety_triggered", issues=output_scan.issues)
            llm_output = llm_output.model_copy(
                update={"rationale": output_scan.sanitized_rationale}
            )
        model_judgment = llm_output

    # ── Step 5: Deterministic guardrails ──────────────────────────────────────
    guard = apply_guardrails(
        llm_output=llm_output,
        cleaned_text=prep.cleaned_text,
        is_trivial=prep.is_trivial and not missing_text,
        injection_flagged_high=injection_flagged_high,
        missing_text=missing_text,
        output_flagged=output_flagged,
        content_signals=signals.signals,
    )

    log.info(
        "pipeline_complete",
        category=guard.category,
        priority=guard.priority,
        needs_human_review=guard.needs_human_review,
        rules_applied=guard.rules_applied,
        is_llm_fallback=is_llm_fallback,
    )

    # ── Step 6: Assemble result ───────────────────────────────────────────────
    return TriageResult(
        ticket_id=ticket.ticket_id,
        original_text=ticket.text,
        cleaned_text=prep.cleaned_text,
        category=guard.category,
        priority=guard.priority,
        sentiment=guard.sentiment,
        customer_impact=guard.customer_impact,
        needs_human_review=guard.needs_human_review,
        rationale=llm_output.rationale,
        model_judgment=model_judgment,
        field_overrides=guard.overrides,
        guardrails_applied=guard.rules_applied,
        preprocessing_applied=prep.transforms_applied,
        security_flags=security_flags,
        input_warnings=warnings,
        llm_model=model_name,
        prompt_version="" if is_llm_fallback else get_prompt().ref,
        is_llm_fallback=is_llm_fallback,
        processing_time_ms=int((time.monotonic() - start) * 1000),
    )


def _safe_default(
    ticket: TicketInput,
    model_name: str,
    baseline: LLMTriageOutput,
    warnings: Sequence[InputWarning],
) -> TriageResult:
    """Result for a ticket whose pipeline run did not complete."""
    return TriageResult(
        ticket_id=ticket.ticket_id,
        original_text=ticket.text,
        cleaned_text=ticket.text,
        category=baseline.category,
        priority=baseline.priority,
        sentiment=baseline.sentiment,
        customer_impact=baseline.customer_impact,
        needs_human_review=True,
        rationale=baseline.rationale,
        input_warnings=list(warnings),
        llm_model=model_name,
        is_llm_fallback=True,
    )


async def process_batch(
    tickets: Sequence[TicketInput],
    model_name: str,
    input_warnings: Sequence[Sequence[InputWarning]] | None = None,
    timeout: float | None = None,
) -> list[TriageResult]:
    """
    Process a batch of tickets concurrently (bounded by LLM_CONCURRENCY).

    Each ticket is independent: an error or a blown time budget on one ticket yields a
    safe needs-human-review result for that ticket, and results keep input order.
    """
    settings = get_settings()
    warnings = input_warnings or [() for _ in tickets]
    semaphore = asyncio.Semaphore(settings.llm_concurrency)

    async def run(ticket: TicketInput, ticket_warnings: Sequence[InputWarning]) -> TriageResult:
        async with semaphore:
            return await process_ticket(ticket, model_name, ticket_warnings)

    tasks = [asyncio.create_task(run(t, w)) for t, w in zip(tickets, warnings, strict=True)]
    if not tasks:
        return []
    _, pending = await asyncio.wait(tasks, timeout=timeout)
    for task in pending:
        task.cancel()
    if pending:
        logger.warning("batch_timeout", unfinished=len(pending), timeout_s=timeout)
        await asyncio.gather(*pending, return_exceptions=True)

    results: list[TriageResult] = []
    for ticket, ticket_warnings, task in zip(tickets, warnings, tasks, strict=True):
        if task.cancelled():
            results.append(_safe_default(ticket, model_name, TIMEOUT_RESULT, ticket_warnings))
        elif (exc := task.exception()) is not None:
            logger.error(
                "ticket_processing_error",
                ticket_id=ticket.ticket_id,
                error_type=type(exc).__name__,
                error=str(exc)[:200],
            )
            results.append(_safe_default(ticket, model_name, ERROR_RESULT, ticket_warnings))
        else:
            results.append(task.result())
    return results
