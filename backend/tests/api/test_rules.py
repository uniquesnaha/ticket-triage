"""Rules endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.triage.guardrails import RULES


def test_lists_every_rule_with_description(client: TestClient) -> None:
    resp = client.get("/api/v1/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert [r["name"] for r in rules] == [r.name for r in RULES]
    assert all(r["description"] for r in rules)


def test_rule_effects_are_serialised(client: TestClient) -> None:
    rules = {r["name"]: r for r in client.get("/api/v1/rules").json()}
    assert rules["OUTAGE_CRITICAL"]["sets"]["priority"] == "critical"
    assert rules["NOT_URGENT"]["max_priority"] == "medium"
    assert rules["MISSING_TEXT"]["condition"] == "Ticket text is empty"
