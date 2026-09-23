"""API endpoint tests."""

from __future__ import annotations

import csv
import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.schema import Category, CustomerImpact, LLMTriageOutput, Priority, Sentiment


def make_llm_output(**kwargs: object) -> LLMTriageOutput:
    defaults = {
        "category": Category.BUG,
        "priority": Priority.MEDIUM,
        "sentiment": Sentiment.NEUTRAL,
        "customer_impact": CustomerImpact.SINGLE_CUSTOMER,
        "needs_human_review": False,
        "rationale": "Standard test response.",
    }
    defaults.update(kwargs)
    return LLMTriageOutput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def mock_llm():
    with patch("app.triage.pipeline.classify_ticket") as m:
        m.return_value = (make_llm_output(), False)
        yield m


class TestAuth:
    def test_no_api_key_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/triage", json={"tickets": [{"ticket_id": "T1", "text": "test"}]}
        )
        assert resp.status_code == 401

    def test_wrong_api_key_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/triage",
            json={"tickets": [{"ticket_id": "T1", "text": "test"}]},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_correct_api_key_accepted(
        self, client: TestClient, auth_headers: dict, mock_llm: AsyncMock
    ) -> None:
        resp = client.post(
            "/api/v1/triage",
            json={"tickets": [{"ticket_id": "T1", "text": "My payment failed."}]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_open_mode_when_no_key_configured(
        self, client: TestClient, mock_llm: AsyncMock
    ) -> None:
        from app.core.config import get_settings

        settings = get_settings()
        original = settings.triage_api_key
        settings.triage_api_key = None
        try:
            resp = client.post(
                "/api/v1/triage",
                json={"tickets": [{"ticket_id": "T1", "text": "My payment failed."}]},
            )
            health = client.get("/api/v1/health").json()
        finally:
            settings.triage_api_key = original
        assert resp.status_code == 200
        assert health["auth_required"] is False


class TestTriageJSON:
    def test_returns_correct_structure(
        self, client: TestClient, auth_headers: dict, mock_llm: AsyncMock
    ) -> None:
        resp = client.post(
            "/api/v1/triage",
            json={"tickets": [{"ticket_id": "T001", "text": "I was charged twice."}]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "results" in data
        assert "by_category" in data
        assert "by_priority" in data
        result = data["results"][0]
        assert result["ticket_id"] == "T001"
        assert "category" in result
        assert "priority" in result
        assert "preprocessing_applied" in result
        assert "guardrails_applied" in result

    def test_request_id_in_response(
        self, client: TestClient, auth_headers: dict, mock_llm: AsyncMock
    ) -> None:
        resp = client.post(
            "/api/v1/triage",
            json={"tickets": [{"ticket_id": "T1", "text": "test ticket"}]},
            headers=auth_headers,
        )
        assert "x-request-id" in resp.headers

    def test_empty_tickets_rejected(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post("/api/v1/triage", json={"tickets": []}, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_ticket_id_rejected(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/triage",
            json={"tickets": [{"ticket_id": "T1; DROP TABLE tickets--", "text": "test"}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_too_many_tickets_rejected(self, client: TestClient, auth_headers: dict) -> None:
        tickets = [{"ticket_id": f"T{i}", "text": "test ticket text here"} for i in range(51)]
        resp = client.post("/api/v1/triage", json={"tickets": tickets}, headers=auth_headers)
        assert resp.status_code == 422


class TestCSVUpload:
    def make_csv(self, rows: list[dict]) -> bytes:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["ticket_id", "text"])
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue().encode()

    def test_valid_csv_upload(
        self, client: TestClient, auth_headers: dict, mock_llm: AsyncMock
    ) -> None:
        csv_data = self.make_csv([{"ticket_id": "T001", "text": "My login is broken."}])
        resp = client.post(
            "/api/v1/triage/upload",
            files={"file": ("test.csv", csv_data, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_missing_column_rejected(self, client: TestClient, auth_headers: dict) -> None:
        csv_data = b"id,message\nT001,test"
        resp = client.post(
            "/api/v1/triage/upload",
            files={"file": ("test.csv", csv_data, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_empty_csv_rejected(self, client: TestClient, auth_headers: dict) -> None:
        csv_data = b"ticket_id,text\n"
        resp = client.post(
            "/api/v1/triage/upload",
            files={"file": ("test.csv", csv_data, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_missing_text_row_still_produces_result(
        self, client: TestClient, auth_headers: dict, mock_llm: AsyncMock
    ) -> None:
        csv_data = b"ticket_id,text\nT1,My login is broken.\nT2,\n"
        resp = client.post(
            "/api/v1/triage/upload",
            files={"file": ("test.csv", csv_data, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert [r["ticket_id"] for r in results] == ["T1", "T2"]
        assert results[1]["needs_human_review"] is True
        assert results[1]["input_warnings"] == ["missing_text"]
        assert mock_llm.call_count == 1  # blank row never reaches the model

    def test_oversized_file_rejected(self, client: TestClient, auth_headers: dict) -> None:
        big = b"ticket_id,text\n" + b"T1," + b"x" * (4 * 1024 * 1024 + 10) + b"\n"
        resp = client.post(
            "/api/v1/triage/upload",
            files={"file": ("big.csv", big, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 413
        assert resp.headers["content-type"] == "application/problem+json"

    def test_wrong_file_type_rejected(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/triage/upload",
            files={"file": ("x.png", b"\x89PNG", "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestSecurityHeaders:
    def test_api_responses_carry_security_headers(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert "default-src 'none'" in resp.headers["content-security-policy"]

    def test_untrusted_host_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health", headers={"Host": "evil.example.com"})
        assert resp.status_code == 400

    def test_malformed_request_id_is_replaced(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health", headers={"X-Request-ID": "bad id\r\ninjected"})
        assert resp.headers["x-request-id"] != "bad id\r\ninjected"
