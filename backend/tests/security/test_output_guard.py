"""Tests for post-LLM output safety validator."""

from __future__ import annotations

from app.security.output_guard import find_unsupported_evidence, validate_output


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
        long_rationale = "A" * 401
        result = validate_output(long_rationale)
        assert "rationale_too_long" in result.issues

    def test_forbidden_content_blocked(self) -> None:
        malicious = "Ticket is critical. <script>alert('xss')</script> Priority: high."
        result = validate_output(malicious)
        assert not result.is_safe
        assert "forbidden_content_detected" in result.issues


class TestEvidenceGrounding:
    SOURCE = ["I was charged twice for order 8841. Please refund the duplicate charge."]

    def test_verbatim_quote_and_number_pass(self) -> None:
        rationale = 'Customer reports being "charged twice" for order 8841.'
        result = validate_output(rationale, self.SOURCE)
        assert result.is_safe

    def test_quote_is_case_insensitive(self) -> None:
        rationale = 'Ticket says "Charged Twice" which indicates a billing issue.'
        assert validate_output(rationale, self.SOURCE).is_safe

    def test_invented_quote_rejected(self) -> None:
        rationale = 'Customer says "I will cancel my subscription" so this is urgent.'
        result = validate_output(rationale, self.SOURCE)
        assert not result.is_safe
        assert "unsupported_evidence" in result.issues

    def test_invented_number_rejected(self) -> None:
        rationale = "Duplicate charge of $49.99 on order 8841 requires a refund."
        result = validate_output(rationale, self.SOURCE)
        assert "unsupported_evidence" in result.issues
        assert find_unsupported_evidence(rationale, self.SOURCE) == ["49.99"]

    def test_grounding_skipped_without_sources(self) -> None:
        assert validate_output('Customer says "something else entirely".').is_safe
