"""All Pydantic models for the application — request, response, and LLM schemas."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings

# ── Enumerations ─────────────────────────────────────────────────────────────


class Category(StrEnum):
    BILLING = "billing"
    AUTH = "auth"
    OUTAGE = "outage"
    FEATURE_REQUEST = "feature_request"
    SHIPPING = "shipping"
    SECURITY = "security"
    BUG = "bug"
    SPAM = "spam"
    UNKNOWN = "unknown"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Priority ordering for ceiling enforcement (higher index = higher priority)
PRIORITY_ORDER = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


class CustomerImpact(StrEnum):
    ALL_CUSTOMERS = "all_customers"
    MULTIPLE_CUSTOMERS = "multiple_customers"
    SINGLE_CUSTOMER = "single_customer"
    NONE = "none"


class SecurityFlag(StrEnum):
    INJECTION_ATTEMPT = "injection_attempt"
    EXCESSIVE_LENGTH = "excessive_length"
    UNICODE_ANOMALY = "unicode_anomaly"


class InputWarning(StrEnum):
    """Data-quality problems in the input row that were handled deterministically."""

    MISSING_TICKET_ID = "missing_ticket_id"
    MISSING_TEXT = "missing_text"
    DUPLICATE_TICKET_ID = "duplicate_ticket_id"
    TEXT_TRUNCATED = "text_truncated"


TICKET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-.]+$")


# ── LLM Output Schema (only what the model fills) ────────────────────────────


class LLMTriageOutput(BaseModel):
    """Strict schema passed to LangChain with_structured_output().
    The LLM is constrained to fill ONLY these fields.
    """

    category: Category
    priority: Priority
    sentiment: Sentiment
    customer_impact: CustomerImpact
    needs_human_review: bool
    rationale: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description=(
            "1-3 concise sentences justifying the classification. Quote exact phrases "
            "from the ticket in double quotes; do not state anything the ticket does not say."
        ),
    )


# ── API Request Models ────────────────────────────────────────────────────────


class TicketInput(BaseModel):
    ticket_id: str = Field(..., min_length=1, max_length=50)
    # Blank text is allowed: it is a missing field, handled deterministically downstream.
    text: str = Field(default="")

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, v: str) -> str:
        if not TICKET_ID_PATTERN.match(v):
            raise ValueError(
                "ticket_id must contain only alphanumeric characters, hyphens, underscores, or dots"
            )
        return v

    @field_validator("text")
    @classmethod
    def validate_text_length(cls, v: str) -> str:
        max_len = get_settings().max_ticket_length
        if len(v) > max_len:
            raise ValueError(f"Ticket text exceeds {max_len} characters")
        return v


class TriageBatchRequest(BaseModel):
    tickets: list[TicketInput] = Field(..., min_length=1)

    @field_validator("tickets")
    @classmethod
    def validate_batch_size(cls, v: list[TicketInput]) -> list[TicketInput]:
        max_batch = get_settings().max_tickets_per_batch
        if len(v) > max_batch:
            raise ValueError(f"At most {max_batch} tickets per batch")
        return v


# ── API Response Models ───────────────────────────────────────────────────────


class FieldOverride(BaseModel):
    """One deterministic change to a model-derived field."""

    field: str
    model_value: str | bool
    final_value: str | bool
    rule: str


class TriageResult(BaseModel):
    """Complete triage result: final decision plus a full provenance trail."""

    ticket_id: str
    original_text: str
    cleaned_text: str

    # Final decision (model judgment after deterministic guardrails)
    category: Category
    priority: Priority
    sentiment: Sentiment
    customer_impact: CustomerImpact
    needs_human_review: bool
    rationale: str

    # Provenance — separates model judgment from deterministic rules
    model_judgment: LLMTriageOutput | None = Field(
        default=None,
        description="Raw validated model output before guardrails; null if the model was not used.",
    )
    field_overrides: list[FieldOverride] = Field(default_factory=list)
    guardrails_applied: list[str] = Field(default_factory=list)
    preprocessing_applied: list[str] = Field(default_factory=list)
    security_flags: list[SecurityFlag] = Field(default_factory=list)
    input_warnings: list[InputWarning] = Field(default_factory=list)

    # Metadata
    llm_model: str = ""
    is_llm_fallback: bool = False
    processing_time_ms: int = 0
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TriageBatchResponse(BaseModel):
    results: list[TriageResult]
    total: int
    processing_time_ms: int
    needs_human_review_count: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    model: str


class HealthResponse(BaseModel):
    status: str
    environment: str
    model: str
    version: str
    llm_configured: bool
