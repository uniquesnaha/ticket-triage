"""Deterministic guardrails — override LLM output based on explicit text evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.schema import (
    PRIORITY_ORDER,
    Category,
    CustomerImpact,
    FieldOverride,
    LLMTriageOutput,
    Priority,
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
    rules_applied: list[str] = field(default_factory=list)
    overrides: list[FieldOverride] = field(default_factory=list)


@dataclass
class GuardrailRule:
    """A single deterministic override rule."""

    name: str
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    # Named pipeline condition instead of keywords, e.g. "is_trivial"
    condition: str | None = None
    overrides: dict[str, object] = field(default_factory=dict)
    # Priority ceiling: if set, priority is capped at this maximum
    max_priority: Priority | None = None
    # Sentiment enforcement: prevent the LLM assigning these sentiments
    prevent_sentiments: list[Sentiment] = field(default_factory=list)
    force_sentiment: Sentiment | None = None
    # Skip this rule when a keyword (explicit-evidence) rule has already fired. Used by
    # TRIVIAL_TICKET: "Payment failed" is short, but it is not uninformative.
    yields_to_evidence: bool = False

    def matches(self, text_lower: str, conditions: set[str]) -> bool:
        if self.condition is not None:
            return self.condition in conditions
        return any(kw in text_lower for kw in self.keywords)


# ── Rule definitions ──────────────────────────────────────────────────────────

RULES: list[GuardrailRule] = [
    GuardrailRule(
        name="OUTAGE_CRITICAL",
        description="Ticket describes an outage affecting many or all customers.",
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
    ),
    GuardrailRule(
        name="SECURITY_REVIEW",
        description="Ticket suggests someone else may have accessed the account.",
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
    ),
    GuardrailRule(
        name="PAYMENT_ANOMALY",
        description="Ticket reports a duplicate or failed payment.",
        keywords=[
            "charged twice",
            "double charged",
            "duplicate charge",
            "double charge",
            "billed twice",
            "payment failed",
        ],
        overrides={"category": Category.BILLING, "needs_human_review": True},
    ),
    GuardrailRule(
        name="NOT_URGENT",
        description="Customer explicitly says the issue is not urgent.",
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
    ),
    GuardrailRule(
        name="POSITIVE_SENTIMENT_GUARD",
        description="Ticket uses explicitly positive wording.",
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
    ),
    GuardrailRule(
        name="TRIVIAL_TICKET",
        description="Ticket is too short to classify (skipped if another rule found evidence).",
        condition="is_trivial",
        yields_to_evidence=True,
        overrides={
            "priority": Priority.LOW,
            "needs_human_review": True,
            "category": Category.UNKNOWN,
        },
    ),
    GuardrailRule(
        name="INJECTION_FLAGGED",
        description="Ticket contains instructions aimed at the model; the model is skipped.",
        condition="injection_flagged_high",
        overrides={
            "category": Category.SECURITY,
            "priority": Priority.HIGH,
            "needs_human_review": True,
        },
    ),
    GuardrailRule(
        name="MISSING_TEXT",
        description="Ticket row has no text; it is never sent to the model.",
        condition="missing_text",
        overrides={
            "category": Category.UNKNOWN,
            "priority": Priority.LOW,
            "customer_impact": CustomerImpact.NONE,
            "needs_human_review": True,
        },
    ),
    GuardrailRule(
        name="OUTPUT_SAFETY_REVIEW",
        description="Model rationale leaked the prompt or cited text not in the ticket.",
        condition="output_flagged",
        overrides={"needs_human_review": True},
    ),
]


# ── Engine ────────────────────────────────────────────────────────────────────


def apply_guardrails(
    llm_output: LLMTriageOutput,
    cleaned_text: str,
    is_trivial: bool = False,
    injection_flagged_high: bool = False,
    missing_text: bool = False,
    output_flagged: bool = False,
) -> GuardrailResult:
    """
    Apply all guardrail rules sequentially.

    Rules are non-exclusive — multiple rules may fire on a single ticket. The model's
    rationale is never edited here; every changed field is recorded as a FieldOverride
    so model judgment and deterministic policy stay distinguishable.
    """
    values: dict[str, Any] = {
        "category": llm_output.category,
        "priority": llm_output.priority,
        "sentiment": llm_output.sentiment,
        "customer_impact": llm_output.customer_impact,
        "needs_human_review": llm_output.needs_human_review,
    }
    conditions = {
        name
        for name, active in (
            ("is_trivial", is_trivial),
            ("injection_flagged_high", injection_flagged_high),
            ("missing_text", missing_text),
            ("output_flagged", output_flagged),
        )
        if active
    }
    rules_applied: list[str] = []
    overrides: list[FieldOverride] = []

    def set_field(name: str, value: Any, rule: str) -> None:
        if values[name] != value:
            overrides.append(
                FieldOverride(
                    field=name,
                    model_value=getattr(llm_output, name),
                    final_value=value,
                    rule=rule,
                )
            )
            values[name] = value

    text_lower = cleaned_text.lower()

    evidence_matched = False
    for rule in RULES:
        if not rule.matches(text_lower, conditions):
            continue
        if rule.yields_to_evidence and evidence_matched:
            continue
        evidence_matched = evidence_matched or bool(rule.keywords)
        rules_applied.append(rule.name)

        for field_name, value in rule.overrides.items():
            if field_name == "needs_human_review":
                # Rules may only escalate to human review, never clear it.
                value = values[field_name] or bool(value)
            set_field(field_name, value, rule.name)

        if rule.max_priority is not None and PRIORITY_ORDER.index(
            values["priority"]
        ) > PRIORITY_ORDER.index(rule.max_priority):
            set_field("priority", rule.max_priority, rule.name)

        if rule.force_sentiment and values["sentiment"] in rule.prevent_sentiments:
            set_field("sentiment", rule.force_sentiment, rule.name)

    # Collapse repeated changes to one entry per field (first model value → final value).
    collapsed: dict[str, FieldOverride] = {}
    for ov in overrides:
        if ov.field in collapsed:
            collapsed[ov.field] = collapsed[ov.field].model_copy(
                update={"final_value": ov.final_value, "rule": ov.rule}
            )
        else:
            collapsed[ov.field] = ov
    final_overrides = [ov for ov in collapsed.values() if ov.model_value != ov.final_value]

    return GuardrailResult(
        category=values["category"],
        priority=values["priority"],
        sentiment=values["sentiment"],
        customer_impact=values["customer_impact"],
        needs_human_review=values["needs_human_review"],
        rules_applied=rules_applied,
        overrides=final_overrides,
    )
