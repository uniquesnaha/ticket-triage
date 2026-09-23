"""All Pydantic models for the application — request, response, and LLM schemas."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ─────────────────────────────────────────────────────────────


class Category(str, Enum):
    BILLING = "billing"
    AUTH = "auth"
    OUTAGE = "outage"
    FEATURE_REQUEST = "feature_request"
    SHIPPING = "shipping"
    SECURITY = "security"
    BUG = "bug"
    SPAM = "spam"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Priority ordering for ceiling enforcement (higher index = higher priority)
PRIORITY_ORDER = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


class CustomerImpact(str, Enum):
    ALL_CUSTOMERS = "all_customers"
    MULTIPLE_CUSTOMERS = "multiple_customers"
    SINGLE_CUSTOMER = "single_customer"
    NONE = "none"


class SecurityFlag(str, Enum):
    INJECTION_ATTEMPT = "injection_attempt"
    EXCESSIVE_LENGTH = "excessive_length"
    UNICODE_ANOMALY = "unicode_anomaly"


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
        max_length=300,
        description="1-3 concise sentences citing specific evidence from the ticket.",
    )


# ── API Request Models ────────────────────────────────────────────────────────


class TicketInput(BaseModel):
    ticket_id: str = Field(..., min_length=1, max_length=50)
    text: str = Field(..., min_length=1, max_length=2000)

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-\.]+$", v):
            raise ValueError("ticket_id must contain only alphanumeric characters, hyphens, underscores, or dots")
        return v

    @field_validator("text")
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Ticket text must not be blank or whitespace-only")
        return v


class TriageBatchRequest(BaseModel):
    tickets: list[TicketInput] = Field(..., min_length=1, max_length=50)


# ── API Response Models ───────────────────────────────────────────────────────


class TriageResult(BaseModel):
    """Complete triage result — combines LLM output with audit annotations."""

    ticket_id: str
    original_text: str
    cleaned_text: str

    # Classification fields (from LLM, potentially overridden by guardrails)
    category: Category
    priority: Priority
    sentiment: Sentiment
    customer_impact: CustomerImpact
    needs_human_review: bool
    rationale: str

    # Audit trail — separates model judgment from deterministic rules
    preprocessing_applied: list[str] = Field(default_factory=list)
    guardrails_applied: list[str] = Field(default_factory=list)
    security_flags: list[SecurityFlag] = Field(default_factory=list)

    # Metadata
    llm_model: str = ""
    is_llm_fallback: bool = False
    processing_time_ms: int = 0
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    docs_enabled: bool


# ── Error Response ────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """RFC 7807 Problem Details."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
