"""Tests for post-LLM output safety validator."""
from __future__ import annotations

import pytest

from app.security.output_guard import validate_output


class TestSafeOutput:
    def test_normal_rationale_passes(self) -> None:
        rationale = "Ticket reports duplicate charge on order 8841. Billing category with high priority for financial review."
        result = validate_output(rationale)
        assert result.is_safe
        assert result.sanitized_rationale == rationale

    def test_feature_request_rationale_passes(self) -> None:
        rationale = "Customer expresses satisfaction with the new dashboard and requests a dark mode feature. Positive sentiment, no operational impact."
        result = validate_output(rationale)
        assert result.is_safe


class TestUnsafeOutput:
    def test_prompt_leakage_detected(self) -> None:
        leaky = "You are a support ticket classification engine. The ticket is critical."
        result = validate_output(leaky)
        assert not result.is_safe
        assert "prompt_leakage_detected" in result.issues
        assert "[OUTPUT_SAFETY_TRIGGERED]" in result.sanitized_rationale

    def test_sentinel_leakage(self) -> None:
        leaky = "The text between <<<TICKET_START>>> and <<<TICKET_END>>> indicates billing."
        result = validate_output(leaky)
        assert not result.is_safe

    def test_rationale_too_long(self) -> None:
        long_rationale = "A" * 400
        result = validate_output(long_rationale)
        # Long rationale gets truncated — not necessarily unsafe unless > 300
        # Our validator truncates and marks as issue
        assert "rationale_too_long" in result.issues

    def test_forbidden_content_blocked(self) -> None:
        malicious = "Ticket is critical. <script>alert('xss')</script> Priority: high."
        result = validate_output(malicious)
        assert not result.is_safe
        assert "forbidden_content_detected" in result.issues
