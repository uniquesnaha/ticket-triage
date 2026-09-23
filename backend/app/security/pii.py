"""PII redaction applied before any text reaches the LLM (OWASP LLM02).

Deterministic, pattern-based detection with validation (Luhn for cards, mod-97 for IBANs)
rather than an NER model: it is fast, auditable, and fits a serverless bundle. The model
never needs contact or payment details to classify a ticket, so we redact rather than
tokenise-and-restore. Personal names are not detected (that needs NER); common sign-offs
are removed by the preprocessor instead.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field


def _luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _iban_valid(raw: str) -> bool:
    iban = raw.replace(" ", "").upper()
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(c, 36)) for c in rearranged)
    return int(numeric) % 97 == 1


@dataclass(frozen=True)
class _Detector:
    label: str
    pattern: re.Pattern[str]
    validate: Callable[[str], bool] | None = None


# Order matters: more specific patterns first so their spans are not re-matched.
_DETECTORS: list[_Detector] = [
    _Detector(
        "SECRET",
        re.compile(r"\b(?:sk|gsk|pk|rk|xox[abp])[-_][A-Za-z0-9_-]{16,}\b|\bAKIA[0-9A-Z]{16}\b"),
    ),
    _Detector("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    _Detector(
        "IBAN",
        re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b"),
        _iban_valid,
    ),
    _Detector(
        "CARD",
        re.compile(r"\b(?:\d[ -]?){12,18}\d\b"),
        lambda m: _luhn_valid(re.sub(r"\D", "", m)),
    ),
    _Detector("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    _Detector(
        "PHONE",
        # International (+CC ...) or 10+ digit numbers with separators; bare short
        # numbers such as order IDs ("order 8841") are deliberately not matched.
        re.compile(
            r"(?<![\w+])(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)[ .-]?)?\d{2,4}(?:[ .-]\d{2,4}){1,3}\b"
        ),
        # E.164 allows at most 15 digits, so longer runs (e.g. invalid card numbers) are not phones.
        lambda m: 10 <= len(re.sub(r"\D", "", m)) <= 15,
    ),
    _Detector(
        "IP_ADDRESS",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    ),
]


@dataclass
class RedactionResult:
    text: str
    found: list[str] = field(default_factory=list)  # labels, e.g. ["EMAIL", "PHONE"]


def redact_pii(text: str) -> RedactionResult:
    """Replace detected PII with typed placeholders like ``[EMAIL]``."""
    found: list[str] = []
    for detector in _DETECTORS:

        def replace(match: re.Match[str], d: _Detector = detector) -> str:
            value = match.group(0)
            if d.validate is not None and not d.validate(value):
                return value
            if d.label not in found:
                found.append(d.label)
            return f"[{d.label}]"

        text = detector.pattern.sub(replace, text)
    return RedactionResult(text=text, found=found)


def contains_pii(text: str) -> bool:
    return bool(redact_pii(text).found)
