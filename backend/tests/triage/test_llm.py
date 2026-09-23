"""Tests for the LLM retry policy (no network)."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import AuthenticationError, BadRequestError, RateLimitError
from tenacity import RetryCallState

from app.core.schema import Category, CustomerImpact, LLMTriageOutput, Priority, Sentiment
from app.triage import llm

GOOD = LLMTriageOutput(
    category=Category.BILLING,
    priority=Priority.HIGH,
    sentiment=Sentiment.NEGATIVE,
    customer_impact=CustomerImpact.SINGLE_CUSTOMER,
    needs_human_review=True,
    rationale='Customer was "charged twice".',
)


def _status_error(
    cls: type[Exception],
    status: int,
    body: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Exception:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(status, request=request, json=body or {}, headers=headers)
    return cls("boom", response=response, body=body)  # type: ignore[call-arg]


def _chain_returning(*outcomes: object) -> MagicMock:
    chain = MagicMock()
    chain.ainvoke = AsyncMock(side_effect=list(outcomes))
    return chain


@pytest.fixture(autouse=True)
def no_backoff() -> Iterator[None]:
    """Make tenacity's backoff instant."""
    with patch("asyncio.sleep", new=AsyncMock()):
        yield


class TestRetryPolicy:
    async def test_malformed_output_is_retried_then_succeeds(self) -> None:
        chain = _chain_returning(None, {"not": "a model"}, GOOD)
        with patch.object(llm, "get_chain", return_value=chain):
            result, is_fallback = await llm.classify_ticket("T1", "charged twice")
        assert result == GOOD
        assert is_fallback is False
        assert chain.ainvoke.await_count == 3

    async def test_gives_up_after_max_retries(self) -> None:
        chain = _chain_returning(*[_status_error(RateLimitError, 429) for _ in range(5)])
        with patch.object(llm, "get_chain", return_value=chain):
            result, is_fallback = await llm.classify_ticket("T1", "text")
        assert is_fallback is True
        assert result is llm.FALLBACK_RESULT
        assert chain.ainvoke.await_count == 4  # MAX_RETRIES default

    async def test_auth_error_not_retried(self) -> None:
        chain = _chain_returning(_status_error(AuthenticationError, 401))
        with patch.object(llm, "get_chain", return_value=chain):
            _, is_fallback = await llm.classify_ticket("T1", "text")
        assert is_fallback is True
        assert chain.ainvoke.await_count == 1

    def test_groq_tool_use_failed_is_retryable(self) -> None:
        exc = _status_error(BadRequestError, 400, {"code": "tool_use_failed"})
        assert llm.is_retryable(exc)

    def test_other_bad_request_not_retryable(self) -> None:
        exc = _status_error(BadRequestError, 400, {"code": "invalid_model"})
        assert not llm.is_retryable(exc)


class TestWaitStrategy:
    @staticmethod
    def _state(exc: Exception, attempt: int = 1) -> RetryCallState:
        state = RetryCallState(retry_object=MagicMock(), fn=None, args=(), kwargs={})
        state.attempt_number = attempt
        state.set_exception((type(exc), exc, None))
        return state

    def test_honours_retry_after_on_429(self) -> None:
        exc = _status_error(RateLimitError, 429, headers={"retry-after": "7"})
        assert llm.wait_for_retry(self._state(exc)) == 7.0

    def test_retry_after_is_capped(self) -> None:
        exc = _status_error(RateLimitError, 429, headers={"retry-after": "3600"})
        assert llm.wait_for_retry(self._state(exc)) == llm.MAX_RATE_LIMIT_WAIT

    def test_exponential_backoff_otherwise(self) -> None:
        exc = llm.MalformedOutputError("bad")
        assert 1.0 <= llm.wait_for_retry(self._state(exc, attempt=2)) <= 8.0


class TestReasoningEffort:
    def test_auto_low_for_gpt_oss(self) -> None:
        from app.core.config import Settings

        s = Settings(model_name="openai/gpt-oss-120b")
        assert s.effective_reasoning_effort == "low"

    def test_auto_unset_for_other_models(self) -> None:
        from app.core.config import Settings

        s = Settings(model_name="llama-3.3-70b-versatile")
        assert s.effective_reasoning_effort is None

    def test_none_disables(self) -> None:
        from app.core.config import Settings

        s = Settings(model_name="openai/gpt-oss-120b", llm_reasoning_effort="none")
        assert s.effective_reasoning_effort is None
