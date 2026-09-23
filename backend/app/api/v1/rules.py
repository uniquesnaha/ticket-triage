"""Read-only view of the deterministic guardrail rules (public, for the UI and auditors)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.triage.guardrails import RULES

router = APIRouter()

CONDITION_LABELS = {
    "is_trivial": "Ticket is two words or fewer",
    "injection_flagged_high": "Prompt-injection pattern detected",
    "missing_text": "Ticket text is empty",
    "output_flagged": "Model rationale failed output checks",
    "safety_risk": "Text mentions self-harm or violence",
    "legal_threat": "Text mentions lawyers, lawsuits, chargebacks or regulators",
    "abusive_language": "Text contains profanity or insults",
}


class RuleInfo(BaseModel):
    name: str
    description: str
    keywords: list[str]
    condition: str | None
    sets: dict[str, str | bool]
    max_priority: str | None
    min_priority: str | None
    corrects_sentiment_to: str | None


@router.get("/rules", response_model=list[RuleInfo], summary="List guardrail rules")
async def list_rules() -> list[RuleInfo]:
    return [
        RuleInfo(
            name=rule.name,
            description=rule.description,
            keywords=rule.keywords,
            condition=CONDITION_LABELS.get(rule.condition, rule.condition)
            if rule.condition
            else None,
            sets={k: v if isinstance(v, bool) else str(v) for k, v in rule.overrides.items()},
            max_priority=str(rule.max_priority) if rule.max_priority else None,
            min_priority=str(rule.min_priority) if rule.min_priority else None,
            corrects_sentiment_to=str(rule.force_sentiment) if rule.force_sentiment else None,
        )
        for rule in RULES
    ]
