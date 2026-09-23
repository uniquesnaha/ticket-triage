"""Tests for PII redaction."""

from __future__ import annotations

import pytest

from app.security.pii import contains_pii, redact_pii


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("email me at jane.doe+billing@example.co.uk please", "EMAIL"),
        ("call +1 415 555 0134 after 5pm", "PHONE"),
        ("my number is (020) 7946-0958", "PHONE"),
        ("card 4111 1111 1111 1111 was charged", "CARD"),
        ("card 4111-1111-1111-1111 was charged", "CARD"),
        ("SSN 123-45-6789 on file", "SSN"),
        ("refund to GB82 WEST 1234 5698 7654 32", "IBAN"),
        ("login from 203.0.113.42 was not me", "IP_ADDRESS"),
        ("I pasted my key gsk_abcdefghijklmnopqrstuvwx by mistake", "SECRET"),
    ],
)
def test_detects_and_redacts(text: str, label: str) -> None:
    result = redact_pii(text)
    assert label in result.found
    assert f"[{label}]" in result.text


@pytest.mark.parametrize(
    "text",
    [
        "I was charged twice for order 8841.",  # order IDs are not phone numbers
        "Invoice 2024-0045 is wrong",
        "It worked on version 3.2.1 yesterday",
        "card 4111 1111 1111 1112 failed",  # fails the Luhn check
        "Production is down for every customer in our region!!!",
    ],
)
def test_leaves_non_pii_alone(text: str) -> None:
    result = redact_pii(text)
    assert result.found == []
    assert result.text == text


def test_multiple_types_in_one_ticket() -> None:
    result = redact_pii("Email a@b.io or call 415-555-0134, card 5555 5555 5555 4444.")
    assert set(result.found) == {"EMAIL", "PHONE", "CARD"}
    assert "@" not in result.text
    assert "5555" not in result.text


def test_contains_pii() -> None:
    assert contains_pii("reach me at bob@example.com")
    assert not contains_pii("reach me by replying here")
