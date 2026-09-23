"""Tests for abuse / legal-threat / safety detection."""

from __future__ import annotations

import pytest

from app.security.content_signals import detect_content_signals


@pytest.mark.parametrize(
    ("text", "signal"),
    [
        ("Your garbage app broke again, fix this shit now", "abusive_language"),
        ("WTF is going on with billing", "abusive_language"),
        ("If this isn't fixed today we will take legal action", "legal_threat"),
        ("My lawyer will be in touch", "legal_threat"),
        ("I am filing a chargeback with my bank", "legal_threat"),
        ("If my account isn't restored I'm going to hurt myself", "safety_risk"),
        ("I don't want to live like this anymore", "safety_risk"),
    ],
)
def test_detects_signal(text: str, signal: str) -> None:
    assert signal in detect_content_signals(text)


@pytest.mark.parametrize(
    "text",
    [
        "Hello, the shipment arrived late",  # "hell" inside "hello"
        "Please assess the classification",  # "ass" inside words
        "The export is broken and I am frustrated",
        "Can you check the invoice for our legal entity name?",
        "I lost my shift schedule after the update",
    ],
)
def test_no_false_positives(text: str) -> None:
    assert detect_content_signals(text).signals == []
