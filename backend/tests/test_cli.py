"""Tests for the command-line entrypoint (LLM mocked)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app import cli
from app.core.logging import configure_logging
from app.core.schema import Category, CustomerImpact, LLMTriageOutput, Priority, Sentiment

DATASET = Path(__file__).parents[2] / "data" / "project_1.csv"

REQUIRED_FIELDS = {
    "ticket_id",
    "category",
    "priority",
    "sentiment",
    "customer_impact",
    "needs_human_review",
    "rationale",
}


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    # The CLI points logging at (captured) stderr; restore it for the other tests.
    yield
    configure_logging()


@pytest.fixture
def mock_llm():
    output = LLMTriageOutput(
        category=Category.BUG,
        priority=Priority.MEDIUM,
        sentiment=Sentiment.NEUTRAL,
        customer_impact=CustomerImpact.SINGLE_CUSTOMER,
        needs_human_review=False,
        rationale="Standard classification from LLM.",
    )
    with patch("app.triage.pipeline.classify_ticket", new=AsyncMock(return_value=(output, False))):
        yield


def test_one_json_object_per_input_row(mock_llm: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(DATASET)]) == cli.EXIT_OK
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 10
    records = [json.loads(line) for line in lines]
    assert [r["ticket_id"] for r in records] == [f"T{i:03d}" for i in range(1, 11)]
    for record in records:
        assert REQUIRED_FIELDS <= record.keys()


def test_json_array_output_to_file(mock_llm: None, tmp_path: Path) -> None:
    out = tmp_path / "results.json"
    assert cli.main([str(DATASET), "--format", "json", "-o", str(out)]) == cli.EXIT_OK
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 10


def test_missing_file_is_input_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["does-not-exist.csv"]) == cli.EXIT_INPUT_ERROR
    assert "cannot read" in capsys.readouterr().err


def test_bad_csv_is_input_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("id,message\nT1,x\n", encoding="utf-8")
    assert cli.main([str(bad)]) == cli.EXIT_INPUT_ERROR
    assert "missing required columns" in capsys.readouterr().err
