"""Deterministic text preprocessing — applied before the LLM sees the ticket."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class PreprocessResult:
    cleaned_text: str
    transforms_applied: list[str] = field(default_factory=list)
    is_trivial: bool = False


# ── Pattern Libraries ─────────────────────────────────────────────────────────

DEVICE_SIGNATURE_PATTERNS = [
    r"sent\s+from\s+my\s+(iphone|android|ipad|samsung|pixel|blackberry|windows\s+phone|galaxy|huawei|oneplus)",
    r"sent\s+from\s+(my\s+)?mobile(\s+device)?",
    r"get\s+outlook\s+for\s+(android|ios)",
    r"sent\s+via\s+\w+(\s+app)?",
    r"typed\s+on\s+my\s+\w+",
    r"downloaded\s+from\s+the\s+app\s+store",
]

EMAIL_CLOSING_PATTERNS = [
    # "Best regards, Alice Smith" or "Best regards,\nAlice"
    r"(best\s+regards?|kind\s+regards?|warm\s+regards?|regards?|sincerely|thanks?\s+(?:and\s+)?regards?|thank\s+you|cheers?|yours?\s+(?:truly|faithfully|sincerely)|with\s+appreciation)\s*[,\.]?\s*\n?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*$",
    # Just "Thanks, Alice"
    r"^thanks?,?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*$",
]

_DEVICE_COMPILED = [re.compile(p, re.IGNORECASE) for p in DEVICE_SIGNATURE_PATTERNS]
_EMAIL_COMPILED = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in EMAIL_CLOSING_PATTERNS]


# ── Individual Transforms ─────────────────────────────────────────────────────


def normalize_unicode(text: str) -> tuple[str, bool]:
    """NFKC normalization to neutralize homoglyph attacks and normalize punctuation."""
    normalized = unicodedata.normalize("NFKC", text)
    return normalized, normalized != text


def strip_device_signatures(text: str) -> tuple[str, bool]:
    """Remove mobile device or email client signatures appended to tickets."""
    changed = False
    for pattern in _DEVICE_COMPILED:
        new_text = pattern.sub("", text).strip()
        if new_text != text:
            text = new_text
            changed = True
    return text, changed


def strip_email_closings(text: str) -> tuple[str, bool]:
    """Remove email sign-off phrases that add noise but no signal."""
    changed = False
    for pattern in _EMAIL_COMPILED:
        new_text = pattern.sub("", text).strip()
        if new_text != text:
            text = new_text
            changed = True
    return text, changed


def deduplicate_fragments(text: str) -> tuple[str, bool]:
    """
    Remove consecutive repeated phrases.
    Handles: "PAYMENT FAILED PAYMENT FAILED PAYMENT FAILED" → "PAYMENT FAILED"
    """
    original = text
    words = text.split()
    if len(words) < 2:
        return text, False

    pattern = re.compile(r"\b(\w+(?:\s+\w+){0,7})\b(?:\s+\1\b)+", re.IGNORECASE)
    prev = None
    curr = text
    while prev != curr:
        prev = curr
        curr = pattern.sub(r"\1", curr)

    return curr, curr != original


def normalize_capitalization(text: str) -> tuple[str, bool]:
    """
    Convert aggressively ALL-CAPS text to sentence case.
    Only applies to sentences where ALL words are uppercase.
    """
    # Split on sentence boundaries
    parts = re.split(r"([.!?]+\s*)", text)
    result_parts = []
    changed = False

    for part in parts:
        # Check if this part (ignoring punctuation) is all uppercase and multi-word
        stripped = re.sub(r"[^A-Za-z\s]", "", part)
        words_only = stripped.split()
        if (
            len(words_only) > 1
            and all(w.isupper() for w in words_only if len(w) > 1)
            and stripped.upper() == stripped
        ):
            result_parts.append(part.capitalize())
            changed = True
        else:
            result_parts.append(part)

    return "".join(result_parts), changed


def collapse_whitespace(text: str) -> tuple[str, bool]:
    """Normalize multiple spaces and newlines to single spaces."""
    new_text = re.sub(r"\s+", " ", text).strip()
    return new_text, new_text != text


def flag_trivial(text: str) -> bool:
    """Mark tickets with insufficient content for classification."""
    word_count = len(text.split())
    return word_count <= 2 or len(text.strip()) < 10


# ── Orchestrator ──────────────────────────────────────────────────────────────


def preprocess(text: str) -> PreprocessResult:
    """
    Apply all deterministic transforms in order.
    Each transform records itself in transforms_applied for full auditability.
    """
    transforms: list[str] = []

    text, changed = normalize_unicode(text)
    if changed:
        transforms.append("UNICODE_NORMALIZE")

    text, changed = strip_device_signatures(text)
    if changed:
        transforms.append("STRIP_DEVICE_SIG")

    text, changed = strip_email_closings(text)
    if changed:
        transforms.append("STRIP_EMAIL_CLOSE")

    text, changed = deduplicate_fragments(text)
    if changed:
        transforms.append("DEDUP_FRAGMENTS")

    text, changed = normalize_capitalization(text)
    if changed:
        transforms.append("NORMALIZE_ALLCAPS")

    text, changed = collapse_whitespace(text)
    if changed:
        transforms.append("COLLAPSE_WHITESPACE")

    is_trivial = flag_trivial(text)
    if is_trivial:
        transforms.append("FLAG_TRIVIAL")

    return PreprocessResult(
        cleaned_text=text,
        transforms_applied=transforms,
        is_trivial=is_trivial,
    )
