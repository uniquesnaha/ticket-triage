"""Tests for versioned prompt loading."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import app.prompts as prompts
from app.core.schema import (
    Category,
    CustomerImpact,
    LLMTriageOutput,
    Priority,
    Sentiment,
    TicketInput,
)
from app.prompts import PromptError, PromptTemplate, load_prompt
from app.triage.llm import PROMPT_VARIABLES, get_prompt
from app.triage.pipeline import process_ticket

VALID = """
[meta]
name = "{name}"
version = "2.1.0"
description = "test prompt"

[prompt]
system = '''You classify tickets.'''
human = '''Ticket: {cleaned_text}'''
"""


@pytest.fixture
def prompt_dir(tmp_path: Path) -> Iterator[Path]:
    load_prompt.cache_clear()
    with patch.object(prompts, "PROMPTS_DIR", tmp_path):
        yield tmp_path
    load_prompt.cache_clear()


def write(directory: Path, name: str, body: str) -> None:
    (directory / f"{name}.toml").write_text(body, encoding="utf-8")


class TestShippedPrompt:
    def test_loads_and_validates(self) -> None:
        prompt = get_prompt()
        assert prompt.name == "triage"
        assert re.fullmatch(r"triage@\d+\.\d+\.\d+#[0-9a-f]{12}", prompt.ref)
        assert "<<<TICKET_START>>>" in prompt.system
        assert "{cleaned_text}" in prompt.human

    def test_fingerprint_tracks_content(self) -> None:
        base = PromptTemplate("p", "1.0.0", "d", "system text", "{cleaned_text}")
        edited = PromptTemplate("p", "1.0.0", "d", "system text!", "{cleaned_text}")
        assert base.fingerprint != edited.fingerprint
        assert base.fingerprint == PromptTemplate(*vars(base).values()).fingerprint


class TestValidation:
    def test_valid_file(self, prompt_dir: Path) -> None:
        write(prompt_dir, "custom", VALID.replace("{name}", "custom"))
        prompt = load_prompt("custom", PROMPT_VARIABLES)
        assert prompt.ref.startswith("custom@2.1.0#")

    @pytest.mark.parametrize(
        ("body", "error"),
        [
            ("not = [valid toml", "invalid TOML"),
            ('[meta]\nname = "bad"', r"\[meta\] and \[prompt\]"),
            (VALID.replace("{name}", "other"), "expected 'bad'"),
            (VALID.replace("{name}", "bad").replace("2.1.0", "v2"), "MAJOR.MINOR.PATCH"),
            (
                VALID.replace("{name}", "bad").replace("You classify", "You {mode} classify"),
                "must not contain template variables",
            ),
            (VALID.replace("{name}", "bad").replace("{cleaned_text}", "{text}"), "missing"),
            (
                VALID.replace("{name}", "bad").replace("{cleaned_text}", "{cleaned_text} {extra}"),
                "unknown variables",
            ),
        ],
    )
    def test_rejects_malformed(self, prompt_dir: Path, body: str, error: str) -> None:
        write(prompt_dir, "bad", body)
        with pytest.raises(PromptError, match=error):
            load_prompt("bad", PROMPT_VARIABLES)

    def test_missing_file(self, prompt_dir: Path) -> None:
        with pytest.raises(PromptError, match="not found"):
            load_prompt("nope", PROMPT_VARIABLES)

    def test_rejects_path_traversal(self) -> None:
        with pytest.raises(PromptError, match="Invalid prompt name"):
            load_prompt("../secrets", PROMPT_VARIABLES)


class TestProvenance:
    async def test_results_record_prompt_version(self) -> None:
        output = LLMTriageOutput(
            category=Category.BUG,
            priority=Priority.MEDIUM,
            sentiment=Sentiment.NEUTRAL,
            customer_impact=CustomerImpact.SINGLE_CUSTOMER,
            needs_human_review=False,
            rationale="Standard classification from LLM.",
        )
        with patch(
            "app.triage.pipeline.classify_ticket", new=AsyncMock(return_value=(output, False))
        ):
            result = await process_ticket(TicketInput(ticket_id="T1", text="Export is broken"), "m")
        assert result.prompt_version == get_prompt().ref

    async def test_no_prompt_version_when_model_skipped(self) -> None:
        result = await process_ticket(TicketInput(ticket_id="T1", text=""), "m")
        assert result.prompt_version == ""
