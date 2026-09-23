"""Deterministic guardrails — override LLM output based on explicit text evidence."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.schema import (
    Category,
    CustomerImpact,
    LLMTriageOutput,
    PRIORITY_ORDER,
    Priority,
    SecurityFlag,
    Sentiment,
)


@dataclass
class GuardrailResult:
    """Guardrail output: the (potentially modified) triage data + audit records."""

    category: Category
    priority: Priority
    sentiment: Sentiment
    customer_impact: CustomerImpact
    needs_human_review: bool
    rationale: str
    rules_applied: list[str] = field(default_factory=list)


@dataclass
class GuardrailRule:
    """A single deterministic override rule."""

    name: str
    keywords: list[str] = field(default_factory=list)
    condition: str | None = None  # "is_trivial" | "injection_flagged_high"
    overrides: dict[str, object] = field(default_factory=dict)
    # Priority ceiling: if set, priority is capped at this maximum
    max_priority: Priority | None = None
    # Sentiment enforcement: prevent the LLM assigning these sentiments
    prevent_sentiments: list[Sentiment] = field(default_factory=list)
    force_sentiment: Sentiment | None = None
    rationale_note: str = ""

    def matches(self, text_lower: str, is_trivial: bool, injection_high: bool) -> bool:
        if self.condition == "is_trivial":
            return is_trivial
        if self.condition == "injection_flagged_high":
            return injection_high
        return any(kw in text_lower for kw in self.keywords)


# ── Rule definitions ──────────────────────────────────────────────────────────

RULES: list[GuardrailRule] = [
    GuardrailRule(
        name="OUTAGE_CRITICAL",
        keywords=[
            "production is down",
            "prod is down",
            "every customer",
            "all customers",
            "entire region",
            "whole region",
            "down for everyone",
            "complete outage",
            "system-wide",
            "systemwide",
        ],
        overrides={
            "priority": Priority.CRITICAL,
            "customer_impact": CustomerImpact.ALL_CUSTOMERS,
            "needs_human_review": True,
        },
        rationale_note="[RULE:OUTAGE_CRITICAL — broad customer impact keyword detected in ticket]",
    ),
    GuardrailRule(
        name="SECURITY_REVIEW",
        keywords=[
            "accessed our account",
            "someone may have",
            "may have accessed",
            "unauthorized access",
            "account breach",
            "account compromised",
            "account hacked",
            "suspicious login",
            "suspicious activity",
            "security incident",
        ],
        overrides={
            "category": Category.SECURITY,
            "needs_human_review": True,
            "priority": Priority.HIGH,
        },
        rationale_note="[RULE:SECURITY_REVIEW — potential account compromise language detected]",
    ),
    GuardrailRule(
        name="PAYMENT_ANOMALY",
        keywords=[
            "charged twice",
            "double charged",
            "duplicate charge",
            "double charge",
            "billed twice",
            "payment failed",
        ],
        overrides={"needs_human_review": True},
        rationale_note="[RULE:PAYMENT_ANOMALY — financial anomaly requires human verification]",
    ),
    GuardrailRule(
        name="NOT_URGENT",
        keywords=[
            "not urgent",
            "no rush",
            "not a rush",
            "whenever you can",
            "whenever convenient",
            "low priority",
            "take your time",
            "not time-sensitive",
        ],
        max_priority=Priority.MEDIUM,
        rationale_note="[RULE:NOT_URGENT — ticket explicitly states low urgency]",
    ),
    GuardrailRule(
        name="POSITIVE_SENTIMENT_GUARD",
        keywords=[
            "love the",
            "love your",
            "love this",
            "great feature",
            "great product",
            "amazing",
            "fantastic",
            "awesome",
            "wonderful",
            "excellent service",
        ],
        prevent_sentiments=[Sentiment.URGENT, Sentiment.NEGATIVE],
        force_sentiment=Sentiment.POSITIVE,
        rationale_note="[RULE:POSITIVE_SENTIMENT — explicit positive language overrides model sentiment]",
    ),
    GuardrailRule(
        name="TRIVIAL_TICKET",
        condition="is_trivial",
        overrides={
            "priority": Priority.LOW,
            "needs_human_review": True,
            "category": Category.UNKNOWN,
        },
        rationale_note="[RULE:TRIVIAL_TICKET — insufficient content to classify accurately]",
    ),
    GuardrailRule(
        name="INJECTION_FLAGGED",
        condition="injection_flagged_high",
        overrides={
            "category": Category.SECURITY,
            "priority": Priority.HIGH,
            "needs_human_review": True,
        },
        rationale_note="[RULE:INJECTION_FLAGGED — potential prompt injection detected; LLM bypassed]",
    ),
]


# ── Engine ────────────────────────────────────────────────────────────────────


def apply_guardrails(
    llm_output: LLMTriageOutput,
    cleaned_text: str,
    is_trivial: bool = False,
    injection_flagged_high: bool = False,
) -> GuardrailResult:
    """
    Apply all guardrail rules sequentially.
    Rules are non-exclusive — multiple rules may fire on a single ticket.
    Each applied rule is recorded in rules_applied for full auditability.
    """
    # Start with LLM values
    category = llm_output.category
    priority = llm_output.priority
    sentiment = llm_output.sentiment
    customer_impact = llm_output.customer_impact
    needs_human_review = llm_output.needs_human_review
    rationale = llm_output.rationale
    rules_applied: list[str] = []

    text_lower = cleaned_text.lower()

    for rule in RULES:
        if not rule.matches(text_lower, is_trivial, injection_flagged_high):
            continue

        rules_applied.append(rule.name)

        # Apply field overrides
        for field_name, value in rule.overrides.items():
            match field_name:
                case "category":
                    category = value  # type: ignore[assignment]
                case "priority":
                    priority = value  # type: ignore[assignment]
                case "customer_impact":
                    customer_impact = value  # type: ignore[assignment]
                case "needs_human_review":
                    needs_human_review = needs_human_review or bool(value)

        # Priority ceiling
        if rule.max_priority is not None:
            current_idx = PRIORITY_ORDER.index(priority)
            max_idx = PRIORITY_ORDER.index(rule.max_priority)
            if current_idx > max_idx:
                priority = rule.max_priority

        # Sentiment enforcement
        if rule.force_sentiment and sentiment in rule.prevent_sentiments:
            sentiment = rule.force_sentiment

        # Append rule annotation to rationale
        if rule.rationale_note:
            rationale = f"{rationale} {rule.rationale_note}"

    return GuardrailResult(
        category=category,
        priority=priority,
        sentiment=sentiment,
        customer_impact=customer_impact,
        needs_human_review=needs_human_review,
        rationale=rationale[:500],  # hard cap to prevent runaway rationale
        rules_applied=rules_applied,
    )
