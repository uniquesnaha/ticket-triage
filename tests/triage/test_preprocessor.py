"""Tests for the text preprocessor."""
from __future__ import annotations

import pytest

from app.triage.preprocessor import (
    collapse_whitespace,
    deduplicate_fragments,
    flag_trivial,
    normalize_capitalization,
    normalize_unicode,
    preprocess,
    strip_device_signatures,
    strip_email_closings,
)


class TestDeduplication:
    def test_triple_repeated_phrase(self) -> None:
        text = "PAYMENT FAILED PAYMENT FAILED PAYMENT FAILED"
        result, changed = deduplicate_fragments(text)
        assert changed
        assert result.count("PAYMENT FAILED") == 1

    def test_double_repeated_phrase(self) -> None:
        text = "please help me please help me"
        result, changed = deduplicate_fragments(text)
        assert changed

    def test_no_repetition(self) -> None:
        text = "I was charged twice for order 8841"
        result, changed = deduplicate_fragments(text)
        assert not changed
        assert result == text


class TestDeviceSignatures:
    def test_iphone_signature_removed(self) -> None:
        text = "My package hasn't arrived. Sent from my iPhone"
        result, changed = strip_device_signatures(text)
        assert changed
        assert "Sent from my iPhone" not in result
        assert "package" in result

    def test_android_signature_removed(self) -> None:
        text = "Login is broken. Sent from my Android"
        result, changed = strip_device_signatures(text)
        assert changed

    def test_no_signature(self) -> None:
        text = "My package is missing."
        result, changed = strip_device_signatures(text)
        assert not changed


class TestEmailClosings:
    def test_best_regards_removed(self) -> None:
        text = "Is dark mode planned?\nBest regards, Alice"
        result, changed = strip_email_closings(text)
        assert changed
        assert "Best regards" not in result
        assert "Alice" not in result
        assert "dark mode" in result

    def test_kind_regards_removed(self) -> None:
        text = "Can you help me?\nKind regards, Bob Smith"
        result, changed = strip_email_closings(text)
        assert changed

    def test_no_closing(self) -> None:
        text = "My invoice is wrong."
        result, changed = strip_email_closings(text)
        assert not changed


class TestCapitalizationNormalization:
    def test_allcaps_sentence_normalized(self) -> None:
        text = "PAYMENT FAILED PLEASE HELP ME"
        result, changed = normalize_capitalization(text)
        assert changed
        # Should be sentence-case, not all caps
        assert result != text

    def test_mixed_case_unchanged(self) -> None:
        text = "My payment failed. Please help."
        result, changed = normalize_capitalization(text)
        assert not changed


class TestTrivialDetection:
    def test_single_word_trivial(self) -> None:
        assert flag_trivial("question") is True

    def test_very_short_trivial(self) -> None:
        assert flag_trivial("hi") is True

    def test_normal_text_not_trivial(self) -> None:
        assert flag_trivial("I was charged twice for order 8841.") is False


class TestFullPipeline:
    def test_t004_email_closing_stripped(self) -> None:
        text = "Love the new dashboard. Just wondering if dark mode is planned? Best regards, Alice"
        result = preprocess(text)
        assert "STRIP_EMAIL_CLOSE" in result.transforms_applied
        assert "Best regards" not in result.cleaned_text
        assert "dark mode" in result.cleaned_text

    def test_t005_device_sig_stripped(self) -> None:
        text = "My package says delivered but I never received it. Sent from my iPhone"
        result = preprocess(text)
        assert "STRIP_DEVICE_SIG" in result.transforms_applied
        assert "iPhone" not in result.cleaned_text

    def test_t006_dedup_applied(self) -> None:
        text = "PAYMENT FAILED PAYMENT FAILED PAYMENT FAILED"
        result = preprocess(text)
        assert "DEDUP_FRAGMENTS" in result.transforms_applied
        assert result.cleaned_text.upper().count("PAYMENT") == 1

    def test_t009_trivial_flagged(self) -> None:
        text = "question"
        result = preprocess(text)
        assert result.is_trivial
        assert "FLAG_TRIVIAL" in result.transforms_applied
