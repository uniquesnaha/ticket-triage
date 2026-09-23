"""Deterministic content signals that must escalate a ticket regardless of the model.

- abusive_language: profanity or insults aimed at the company/agent. Not censored (the
  model still needs the text to classify), but routed to a human.
- legal_threat: the customer mentions legal action, lawyers or regulators.
- safety_risk: self-harm or threats of violence. Always critical and human-reviewed.

Word-boundary regexes on normalised text; the lists are short and conservative on
purpose (false positives cost a human review, false negatives cost much more for
safety_risk, so that list leans broad).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PROFANITY = [
    r"f+u+c+k\w*",
    r"sh[i1]t\w*",
    r"bullshit",
    r"crap",
    r"bastards?",
    r"assholes?",
    r"idiots?",
    r"morons?",
    r"stupid",
    r"garbage",
    r"wtf",
]

_LEGAL = [
    r"lawyers?",
    r"attorneys?",
    r"legal action",
    r"sue (?:you|your)",
    r"su(?:e|ing) you",
    r"lawsuit",
    r"small claims",
    r"take (?:you|this) to court",
    r"chargeback",
    r"consumer protection",
    r"ombudsman",
    r"report(?:ing)? (?:you|this) to the (?:ftc|bbb|regulator)",
]

_SAFETY = [
    r"(?:kill|hurt|harm) (?:my ?self|me)",
    r"suicid\w*",
    r"end (?:it all|my life)",
    r"don'?t want to live",
    r"(?:kill|hurt|shoot|attack) (?:you|your (?:staff|team|people))",
    r"bomb",
    r"come to your office and",
]


def _compile(words: list[str]) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.IGNORECASE)


_SIGNALS: dict[str, re.Pattern[str]] = {
    "abusive_language": _compile(_PROFANITY),
    "legal_threat": _compile(_LEGAL),
    "safety_risk": _compile(_SAFETY),
}


@dataclass
class ContentSignals:
    signals: list[str] = field(default_factory=list)

    def __contains__(self, name: str) -> bool:
        return name in self.signals


def detect_content_signals(text: str) -> ContentSignals:
    return ContentSignals([name for name, pattern in _SIGNALS.items() if pattern.search(text)])
