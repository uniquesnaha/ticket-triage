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

_LEAKAGE = [re.compile(p, re.IGNORECASE) for p in LEAKAGE_PATTERNS]
_HALLUCINATION = [re.compile(p, re.IGNORECASE) for p in HALLUCINATION_PATTERNS]
_FORBIDDEN = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]

SAFE_FALLBACK_RATIONALE = (
    "Ticket classified by automated system. Rationale was flagged during safety review "
    "and has been withheld. Manual review required. [OUTPUT_SAFETY_TRIGGERED]"
)


def validate_output(rationale: str) -> OutputScanResult:
    """
    Validate the LLM-generated rationale for:
    1. Prompt leakage (system prompt fragments)
    2. Hallucinated claims
    3. Forbidden content (injected code, XSS, etc.)
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

    # Length sanity check
    if len(rationale) > 300:
        issues.append("rationale_too_long")
        rationale = rationale[:297] + "..."

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
