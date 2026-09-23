"""Post-LLM output safety validator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class OutputScanResult:
    is_safe: bool
    issues: list[str] = field(default_factory=list)
    sanitized_rationale: str = ""


# Patterns that indicate prompt leakage (system prompt fragments leaked into rationale)
LEAKAGE_PATTERNS = [
    r"critical\s+security\s+rules",
    r"<<<ticket_start>>>",
    r"<<<ticket_end>>>",
    r"non-negotiable",
    r"classification\s+engine",
    r"you\s+are\s+a\s+support\s+ticket",
    r"your\s+only\s+function",
]

# Patterns that indicate hallucinated external claims
HALLUCINATION_PATTERNS = [
    r"customer\s+(said|stated|mentioned|indicated|told\s+us)\s+they\s+will\s+sue",
    r"will\s+file\s+a\s+lawsuit",
    r"has\s+already\s+contacted\s+a\s+lawyer",
    r"is\s+going\s+to\s+the\s+press",
    r"chargeback\s+has\s+been\s+filed",
]

# Patterns that should never appear in a rationale
FORBIDDEN_PATTERNS = [
    r"\bexecute\b.*\bcommand\b",
    r"\bsystem\b.*\bcall\b",
    r"rm\s+-rf",
    r"DROP\s+TABLE",
    r"<script",
    r"javascript:",
]

# Quoted evidence ("...", “...”) — every quote must exist in the ticket text.
_QUOTE = re.compile(r'"([^"]{3,})"|“([^”]{3,})”')
# Identifiers/amounts (2+ digits) — the model must not invent order numbers, sums, dates.
_NUMBER = re.compile(r"\d[\d,.]*\d")

_LEAKAGE = [re.compile(p, re.IGNORECASE) for p in LEAKAGE_PATTERNS]
_HALLUCINATION = [re.compile(p, re.IGNORECASE) for p in HALLUCINATION_PATTERNS]
_FORBIDDEN = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]

MAX_RATIONALE_LENGTH = 400

SAFE_FALLBACK_RATIONALE = (
    "Ticket classified by automated system. Rationale was flagged during safety review "
    "and has been withheld. Manual review required. [OUTPUT_SAFETY_TRIGGERED]"
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def find_unsupported_evidence(rationale: str, source_texts: list[str]) -> list[str]:
    """Return quoted phrases or numbers in the rationale that no source text contains."""
    haystack = "\n".join(_normalize(t) for t in source_texts)
    unsupported: list[str] = []
    for match in _QUOTE.finditer(rationale):
        quote = _normalize(match.group(1) or match.group(2)).strip(" .,!?;:")
        if quote and quote not in haystack:
            unsupported.append(quote)
    for number in _NUMBER.findall(rationale):
        if number not in haystack:
            unsupported.append(number)
    return unsupported


def validate_output(rationale: str, source_texts: list[str] | None = None) -> OutputScanResult:
    """
    Validate the LLM-generated rationale for:
    1. Prompt leakage (system prompt fragments)
    2. Hallucinated claims (known patterns)
    3. Forbidden content (injected code, XSS, etc.)
    4. Unsupported evidence — quotes or numbers absent from the ticket (when sources given)
    """
    issues: list[str] = []

    for pattern in _LEAKAGE:
        if pattern.search(rationale):
            issues.append("prompt_leakage_detected")
            break

    for pattern in _HALLUCINATION:
        if pattern.search(rationale):
            issues.append("hallucination_detected")
            break

    for pattern in _FORBIDDEN:
        if pattern.search(rationale):
            issues.append("forbidden_content_detected")
            break

    if source_texts is not None and find_unsupported_evidence(rationale, source_texts):
        issues.append("unsupported_evidence")

    # Length sanity check
    if len(rationale) > MAX_RATIONALE_LENGTH:
        issues.append("rationale_too_long")

    if issues:
        return OutputScanResult(
            is_safe=False,
            issues=issues,
            sanitized_rationale=SAFE_FALLBACK_RATIONALE,
        )

    return OutputScanResult(
        is_safe=True,
        issues=[],
        sanitized_rationale=rationale,
    )
