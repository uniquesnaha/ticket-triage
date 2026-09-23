"""Health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "environment" in data
        assert "model" in data
        assert "version" in data
        assert data["llm_configured"] is True

    def test_health_no_auth_required(self, client: TestClient) -> None:
        # Health endpoint should be public
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_has_request_id(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert "x-request-id" in resp.headers

    def test_health_reports_degraded_without_llm_key(self, client: TestClient) -> None:
        from pydantic import SecretStr

        from app.core.config import get_settings

        settings = get_settings()
        original = settings.groq_api_key
        settings.groq_api_key = SecretStr("")
        try:
            data = client.get("/api/v1/health").json()
        finally:
            settings.groq_api_key = original
        assert data["status"] == "degraded"
        assert data["llm_configured"] is False
