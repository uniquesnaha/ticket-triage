"""Triage pipeline — orchestrates preprocessing → LLM → output guard → guardrails."""
from __future__ import annotations

import time

import structlog

from app.core.schema import (
    SecurityFlag,
    TicketInput,
    TriageResult,
)
from app.security.input_guard import RiskLevel, scan_for_injection
from app.security.output_guard import validate_output
from app.triage.guardrails import apply_guardrails
from app.triage.llm import FALLBACK_RESULT, classify_ticket
from app.triage.preprocessor import preprocess

logger = structlog.get_logger()


async def process_ticket(ticket: TicketInput, model_name: str) -> TriageResult:
    """
    Full triage pipeline for a single ticket.

    Pipeline:
      1. Input security scan (injection detection)
      2. Text preprocessing (deterministic cleaning)
      3. LLM classification (skipped for high-risk injections)
      4. Post-LLM output safety validation
      5. Deterministic guardrails (rule overrides)
      6. Assemble final TriageResult with full audit trail
    """
    start_ms = time.monotonic()
    security_flags: list[SecurityFlag] = []
    is_llm_fallback = False

    log = logger.bind(ticket_id=ticket.ticket_id)
    log.info("pipeline_start", text_length=len(ticket.text))

    # ── Step 1: Input security scan ───────────────────────────────────────────
    scan = scan_for_injection(ticket.text)

    if scan.security_flags:
        for flag in scan.security_flags:
            if flag == "unicode_anomaly":
                security_flags.append(SecurityFlag.UNICODE_ANOMALY)
            elif flag == "excessive_length":
                security_flags.append(SecurityFlag.EXCESSIVE_LENGTH)

    if scan.risk_level == RiskLevel.HIGH:
        security_flags.append(SecurityFlag.INJECTION_ATTEMPT)
        log.warning(
            "injection_detected",
            matched_patterns=scan.matched_patterns,
            risk="HIGH",
        )

    # Use normalized text going forward
    normalized_text = scan.normalized_text if scan.normalized_text else ticket.text

    # ── Step 2: Preprocessing ─────────────────────────────────────────────────
    prep = preprocess(normalized_text)
    log.debug("preprocessing_done", transforms=prep.transforms_applied)

    # ── Step 3: LLM classification ────────────────────────────────────────────
    injection_flagged_high = scan.risk_level == RiskLevel.HIGH

    if injection_flagged_high:
        # Do NOT send injection-flagged tickets to the LLM
        log.warning("llm_skipped_injection", ticket_id=ticket.ticket_id)
        llm_output = FALLBACK_RESULT
        is_llm_fallback = True
    else:
        llm_output, is_llm_fallback = await classify_ticket(
            ticket_id=ticket.ticket_id,
            cleaned_text=prep.cleaned_text,
        )

    # ── Step 4: Post-LLM output safety validation ─────────────────────────────
    output_scan = validate_output(llm_output.rationale)
    if not output_scan.is_safe:
        log.warning(
            "output_safety_triggered",
            issues=output_scan.issues,
            ticket_id=ticket.ticket_id,
        )
        # Replace rationale with safe fallback, keep classification
        llm_output = llm_output.model_copy(
            update={"rationale": output_scan.sanitized_rationale}
        )

    # ── Step 5: Deterministic guardrails ──────────────────────────────────────
    guardrail_result = apply_guardrails(
        llm_output=llm_output,
        cleaned_text=prep.cleaned_text,
        is_trivial=prep.is_trivial,
        injection_flagged_high=injection_flagged_high,
    )

    log.info(
        "pipeline_complete",
        category=guardrail_result.category,
        priority=guardrail_result.priority,
        needs_human_review=guardrail_result.needs_human_review,
        rules_applied=guardrail_result.rules_applied,
        is_llm_fallback=is_llm_fallback,
    )

    # ── Step 6: Assemble result ───────────────────────────────────────────────
    elapsed_ms = int((time.monotonic() - start_ms) * 1000)

    return TriageResult(
        ticket_id=ticket.ticket_id,
        original_text=ticket.text,
        cleaned_text=prep.cleaned_text,
        category=guardrail_result.category,
        priority=guardrail_result.priority,
        sentiment=guardrail_result.sentiment,
        customer_impact=guardrail_result.customer_impact,
        needs_human_review=guardrail_result.needs_human_review,
        rationale=guardrail_result.rationale,
        preprocessing_applied=prep.transforms_applied,
        guardrails_applied=guardrail_result.rules_applied,
        security_flags=security_flags,
        llm_model=model_name,
        is_llm_fallback=is_llm_fallback,
        processing_time_ms=elapsed_ms,
    )


async def process_batch(tickets: list[TicketInput], model_name: str) -> list[TriageResult]:
    """
    Process a batch of tickets.
    Each ticket is processed independently — one failure does not block others.
    """
    import asyncio

    tasks = [process_ticket(ticket, model_name) for ticket in tickets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final: list[TriageResult] = []
    for ticket, result in zip(tickets, results, strict=True):
        if isinstance(result, Exception):
            logger.error(
                "ticket_processing_error",
                ticket_id=ticket.ticket_id,
                error=str(result)[:200],
            )
            # Emit a safe fallback result so the batch still completes
            final.append(
                TriageResult(
                    ticket_id=ticket.ticket_id,
                    original_text=ticket.text,
                    cleaned_text=ticket.text,
                    category=FALLBACK_RESULT.category,
                    priority=FALLBACK_RESULT.priority,
                    sentiment=FALLBACK_RESULT.sentiment,
                    customer_impact=FALLBACK_RESULT.customer_impact,
                    needs_human_review=True,
                    rationale=f"Processing error — manual review required. [PIPELINE_ERROR]",
                    is_llm_fallback=True,
                    llm_model=model_name,
                )
            )
        else:
            final.append(result)  # type: ignore[arg-type]

    return final
