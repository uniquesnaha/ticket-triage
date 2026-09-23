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

    def test_health_no_auth_required(self, client: TestClient) -> None:
        # Health endpoint should be public
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_has_request_id(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert "x-request-id" in resp.headers
