"""Prompt injection scanner — pre-LLM security gate."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    CLEAN = "clean"
    LOW = "low"  # Flag + warn but still process
    HIGH = "high"  # Block — do NOT send to LLM


@dataclass
class InjectionScanResult:
    risk_level: RiskLevel
    matched_patterns: list[str] = field(default_factory=list)
    security_flags: list[str] = field(default_factory=list)
    normalized_text: str = ""


# ── Injection pattern library ─────────────────────────────────────────────────
# Each entry: (regex pattern, label, high_risk: bool)
INJECTION_PATTERNS: list[tuple[str, str, bool]] = [
    # Classic instruction override
    (
        r"ignore\s+(all\s+)?(previous\s+|your\s+)?(instructions?|prompt|system|rules?|context)",
        "ignore_instructions",
        True,
    ),
    (
        r"forget\s+(everything|your\s+instructions?|what\s+i\s+said|all\s+previous)",
        "forget_instructions",
        True,
    ),
    (r"\bdisregard\s+(all|previous|your|the)\b", "disregard", True),
    # Identity override
    (
        r"\byou\s+are\s+now\s+(a\s+|an\s+)?(?!support|customer|an?\s+agent)",
        "identity_override",
        True,
    ),
    (r"\bact\s+as\s+(a\s+|an\s+)?\w+\s+(without|that\s+doesn)", "act_as", True),
    (r"\bpretend\s+(you\s+are|to\s+be)\s+", "pretend", True),
    # Jailbreak patterns
    (r"\bjailbreak\b", "jailbreak", True),
    (r"\bdo\s+anything\s+now\b", "dan", True),
    (r"\bsudo\s+mode\b", "sudo_mode", True),
    (r"\bdeveloper\s+mode\b", "dev_mode", True),
    (r"\bgod\s+mode\b", "god_mode", True),
    # Structural injection
    (r"new\s+instructions?\s*:", "new_instructions", True),
    (r"system\s*:\s*[\[\{]", "system_injection", True),
    (r"<\s*(system|instruction|prompt)\s*>", "xml_tag_injection", True),
    (r"\[INST\]|\[\/INST\]", "llama_injection", True),
    (r"<<<\s*(system|instruction|ticket_start|ticket_end).*?>>>", "sentinel_spoof", True),
    # Markdown/format injection
    (r"#{1,6}\s*(instruction|system|override|prompt)", "markdown_header_injection", False),
    (r"---+\s*(system|instruction)", "hr_injection", False),
    # Extraction/exfiltration attempts
    (
        r"(print|repeat|output|reveal|show|tell\s+me)\s+your\s+(system\s+)?(prompt|instructions?)",
        "prompt_extraction",
        True,
    ),
    (
        r"what\s+(are\s+)?your\s+(system\s+)?(instructions?|rules?|prompt)",
        "prompt_extraction_2",
        False,
    ),
    # Override directives
    (r"\boverride\s+(your|the)\s+(instructions?|rules?|system|safety)", "override_directive", True),
    (r"\bbypass\s+(your|the|all)\s+(safety|filter|restriction|guard)", "bypass", True),
]

# Compiled pattern cache
_COMPILED: list[tuple[re.Pattern[str], str, bool]] = [
    (re.compile(pat, re.IGNORECASE | re.DOTALL), label, high)
    for pat, label, high in INJECTION_PATTERNS
]


_HOMOGLYPH_MAP = str.maketrans(
    {
        "а": "a",
        "с": "c",
        "е": "e",
        "о": "o",
        "р": "p",
        "х": "x",
        "у": "y",
        "А": "A",
        "В": "B",
        "С": "C",
        "Е": "E",
        "Н": "H",
        "І": "I",
        "Ј": "J",
        "К": "K",
        "М": "M",
        "О": "O",
        "Р": "P",
        "Ѕ": "S",
        "Т": "T",
        "Х": "X",
        "і": "i",
        "ј": "j",
        "ѕ": "s",
    }
)


def normalize_input(text: str) -> str:
    """NFKC normalization + homoglyph mapping neutralizes attacks (е vs e, а vs a, etc.)."""
    nfkc = unicodedata.normalize("NFKC", text)
    return nfkc.translate(_HOMOGLYPH_MAP)


def scan_for_injection(text: str, max_length: int = 2000) -> InjectionScanResult:
    """
    Multi-stage injection scan.

    Returns RiskLevel.HIGH for tickets that should NOT reach the LLM.
    Returns RiskLevel.LOW for suspicious but low-confidence signals.
    Returns RiskLevel.CLEAN for normal tickets.
    """
    flags: list[str] = []
    matched: list[str] = []
    high_risk_hits = 0

    # Length check — over-long text is truncated and flagged, then still scanned.
    if len(text) > max_length:
        flags.append("excessive_length")
        text = text[:max_length]

    # Unicode normalization — detect and neutralize homoglyphs
    normalized = normalize_input(text)
    if normalized != text:
        flags.append("unicode_anomaly")

    text_to_scan = normalized.lower()

    # Pattern scan
    for compiled_pattern, label, is_high_risk in _COMPILED:
        if compiled_pattern.search(text_to_scan):
            matched.append(label)
            if is_high_risk:
                high_risk_hits += 1

    # Risk determination
    if high_risk_hits >= 1:
        risk = RiskLevel.HIGH
    elif matched:
        risk = RiskLevel.LOW
    else:
        risk = RiskLevel.CLEAN

    return InjectionScanResult(
        risk_level=risk,
        matched_patterns=matched,
        security_flags=flags,
        normalized_text=normalized,
    )
