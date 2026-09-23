"""LangChain chain with Groq (OpenAI-compatible) — structured output with tenacity retry."""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.schema import (
    Category,
    CustomerImpact,
    LLMTriageOutput,
    Priority,
    Sentiment,
)
from app.prompts import PromptTemplate, load_prompt

logger = structlog.get_logger()


# ── Prompt ────────────────────────────────────────────────────────────────────
# The prompt text lives in app/prompts/<name>.toml (versioned, fingerprinted).

PROMPT_VARIABLES = frozenset({"cleaned_text"})


def get_prompt() -> PromptTemplate:
    return load_prompt(get_settings().triage_prompt, PROMPT_VARIABLES)


# ── Deterministic results used when the model is not (successfully) consulted ─


def _baseline(rationale: str) -> LLMTriageOutput:
    return LLMTriageOutput(
        category=Category.UNKNOWN,
        priority=Priority.MEDIUM,
        sentiment=Sentiment.NEUTRAL,
        customer_impact=CustomerImpact.SINGLE_CUSTOMER,
        needs_human_review=True,
        rationale=rationale,
    )


FALLBACK_RESULT = _baseline(
    "Automated classification was unavailable (model call failed after retries); "
    "routed to manual review. [LLM_FALLBACK]"
)
INJECTION_SKIPPED_RESULT = _baseline(
    "Ticket contains instruction-like content and was not sent to the model; "
    "routed to manual review. [LLM_SKIPPED]"
)
MISSING_TEXT_RESULT = _baseline(
    "Ticket has no text, so no classification is possible; routed to manual review. "
    "[MISSING_TEXT]"
)
TIMEOUT_RESULT = _baseline(
    "Ticket was not processed within the batch time budget; routed to manual review. "
    "[BATCH_TIMEOUT]"
)
ERROR_RESULT = _baseline(
    "An internal processing error occurred; routed to manual review. [PIPELINE_ERROR]"
)


# ── LangChain chain factory ───────────────────────────────────────────────────

_chain: Runnable[dict[str, Any], Any] | None = None


def _build_chain() -> Runnable[dict[str, Any], Any]:
    settings = get_settings()

    # gpt-oss models reason before answering; for a short classification task, low effort
    # is as accurate and spends far fewer tokens (which count against Groq's TPM limit).
    model_kwargs: dict[str, Any] = {}
    if settings.effective_reasoning_effort:
        model_kwargs["reasoning_effort"] = settings.effective_reasoning_effort

    llm = ChatOpenAI(
        model=settings.model_name,
        model_kwargs=model_kwargs,
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.llm_timeout,
        max_retries=0,  # tenacity owns retries
    )

    # Constrain the LLM to fill only LLMTriageOutput fields via tool calling
    structured_llm = llm.with_structured_output(LLMTriageOutput, method="function_calling")

    template = get_prompt()
    prompt = ChatPromptTemplate.from_messages(
        [("system", template.system), ("human", template.human)]
    )
    return prompt | structured_llm


def get_chain() -> Runnable[dict[str, Any], Any]:
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


# ── Retry policy ──────────────────────────────────────────────────────────────


class MalformedOutputError(ValueError):
    """The model answered, but not with a valid LLMTriageOutput."""


_RETRYABLE = (
    RateLimitError,
    APIConnectionError,  # includes APITimeoutError
    InternalServerError,
    ValidationError,
    OutputParserException,
    MalformedOutputError,
)


def is_retryable(exc: BaseException) -> bool:
    """Transient API failures and malformed structured output are retried; auth/config
    errors and other 4xx responses are not, since retrying cannot fix them."""
    if isinstance(exc, _RETRYABLE):
        return True
    # Groq returns HTTP 400 "tool_use_failed" when the model emits an invalid tool call.
    if isinstance(exc, BadRequestError):
        return getattr(exc, "code", None) == "tool_use_failed" or "tool_use_failed" in str(exc)
    return False


MAX_RATE_LIMIT_WAIT = 20.0
_backoff = wait_exponential(multiplier=1, min=1, max=8)


def wait_for_retry(retry_state: RetryCallState) -> float:
    """Exponential backoff, except on 429s where the provider's Retry-After is honoured
    (capped) — per-minute token windows usually need longer than the default backoff."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, RateLimitError):
        try:
            retry_after = float(exc.response.headers.get("retry-after", ""))
        except ValueError:
            pass
        else:
            return min(max(retry_after, 1.0), MAX_RATE_LIMIT_WAIT)
    return float(_backoff(retry_state))


async def _invoke(cleaned_text: str) -> LLMTriageOutput:
    settings = get_settings()
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(is_retryable),
        wait=wait_for_retry,
        stop=stop_after_attempt(settings.max_retries),
        reraise=True,
    ):
        with attempt:
            result = await get_chain().ainvoke({"cleaned_text": cleaned_text})
            if not isinstance(result, LLMTriageOutput):
                raise MalformedOutputError(f"Unexpected LLM output type: {type(result).__name__}")
            return result
    raise AssertionError("unreachable")  # pragma: no cover


async def classify_ticket(ticket_id: str, cleaned_text: str) -> tuple[LLMTriageOutput, bool]:
    """
    Classify a single ticket.

    Returns:
        (LLMTriageOutput, is_fallback) — is_fallback=True means the LLM failed and a safe
        deterministic fallback was returned instead.
    """
    if not get_settings().llm_configured:
        logger.error("llm_not_configured", ticket_id=ticket_id)
        return FALLBACK_RESULT, True

    try:
        result = await _invoke(cleaned_text)
    except Exception as exc:
        logger.warning(
            "llm_classification_failed",
            ticket_id=ticket_id,
            error_type=type(exc).__name__,
            error=str(exc)[:200],  # truncate to avoid logging injection payloads
        )
        return FALLBACK_RESULT, True

    logger.info(
        "llm_classification_success",
        ticket_id=ticket_id,
        category=result.category,
        priority=result.priority,
    )
    return result, False
