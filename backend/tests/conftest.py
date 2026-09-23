"""Pytest fixtures and test configuration."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Set test env vars before importing app
# Set test env vars before importing the app (they override any local .env file).
os.environ["GROQ_API_KEY"] = "gsk_test_groq_key_12345"
os.environ["ENVIRONMENT"] = "testing"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["ALLOWED_HOSTS"] = "localhost,testserver"
os.environ["RATE_LIMIT_TRIAGE"] = "1000/minute"
os.environ["RATE_LIMIT_UPLOAD"] = "1000/minute"

from app.core.config import Settings, get_settings  # noqa: E402

# Never read a developer's local .env during tests.
Settings.model_config["env_file"] = None
get_settings.cache_clear()

from app.main import app  # noqa: E402  (import after env setup)


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_tickets() -> list[dict]:
    return [
        {
            "ticket_id": "T001",
            "text": "I was charged twice for order 8841. Please refund the duplicate charge.",
        },
        {
            "ticket_id": "T002",
            "text": "Can't log in after resetting my password. It just loops back to the login page.",
        },
        {"ticket_id": "T003", "text": "Production is down for every customer in our region!!!"},
        {
            "ticket_id": "T004",
            "text": "Love the new dashboard. Just wondering if dark mode is planned? Best regards, Alice",
        },
        {
            "ticket_id": "T005",
            "text": "My package says delivered but I never received it. Sent from my iPhone",
        },
        {"ticket_id": "T006", "text": "PAYMENT FAILED PAYMENT FAILED PAYMENT FAILED"},
        {
            "ticket_id": "T007",
            "text": "The report export is broken. It worked yesterday and now downloads an empty CSV.",
        },
        {
            "ticket_id": "T008",
            "text": "We think someone may have accessed our account. Please advise.",
        },
        {"ticket_id": "T009", "text": "question"},
        {"ticket_id": "T010", "text": "The invoice has a typo in our company name. Not urgent."},
    ]
