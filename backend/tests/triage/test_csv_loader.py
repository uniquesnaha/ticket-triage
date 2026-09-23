"""Tests for CSV parsing and missing-field handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.schema import InputWarning
from app.triage.csv_loader import (
    CSVFormatError,
    ParsedTicket,
    decode_csv_bytes,
    parse_tickets_csv,
)

DATASET = Path(__file__).parents[3] / "data" / "project_1.csv"


def parse(
    content: str, max_text_length: int = 2000, max_rows: int | None = None
) -> list[ParsedTicket]:
    return parse_tickets_csv(content, max_text_length=max_text_length, max_rows=max_rows)


class TestParse:
    def test_supplied_dataset_parses(self) -> None:
        parsed = parse(decode_csv_bytes(DATASET.read_bytes()))
        assert [p.ticket.ticket_id for p in parsed] == [f"T{i:03d}" for i in range(1, 11)]
        assert all(not p.warnings for p in parsed)

    def test_headers_are_case_and_space_insensitive(self) -> None:
        parsed = parse(" Ticket_ID ,TEXT\nT1,hello there\n")
        assert parsed[0].ticket.ticket_id == "T1"
        assert parsed[0].ticket.text == "hello there"

    def test_missing_text_is_kept_with_warning(self) -> None:
        parsed = parse("ticket_id,text\nT1,\nT2,real text here\n")
        assert len(parsed) == 2
        assert parsed[0].warnings == [InputWarning.MISSING_TEXT]

    def test_short_row_treated_as_missing_text(self) -> None:
        parsed = parse("ticket_id,text\nT1\n")
        assert InputWarning.MISSING_TEXT in parsed[0].warnings

    def test_missing_ticket_id_is_generated(self) -> None:
        parsed = parse("ticket_id,text\n,some text\n")
        assert parsed[0].ticket.ticket_id == "ROW-1"
        assert InputWarning.MISSING_TICKET_ID in parsed[0].warnings

    def test_duplicate_ids_flagged(self) -> None:
        parsed = parse("ticket_id,text\nT1,a b c\nT1,d e f\n")
        assert parsed[1].warnings == [InputWarning.DUPLICATE_TICKET_ID]

    def test_long_text_truncated(self) -> None:
        parsed = parse("ticket_id,text\nT1," + "x" * 50 + "\n", max_text_length=10)
        assert len(parsed[0].ticket.text) == 10
        assert InputWarning.TEXT_TRUNCATED in parsed[0].warnings

    def test_bom_is_tolerated(self) -> None:
        parsed = parse(decode_csv_bytes("﻿ticket_id,text\nT1,hi there\n".encode()))
        assert parsed[0].ticket.ticket_id == "T1"


class TestErrors:
    @pytest.mark.parametrize(
        "content",
        ["", "id,message\nT1,x\n", "ticket_id,text\n", "ticket_id,text\nbad id!,x\n"],
    )
    def test_structural_errors(self, content: str) -> None:
        with pytest.raises(CSVFormatError):
            parse(content)

    def test_row_limit(self) -> None:
        with pytest.raises(CSVFormatError, match="maximum of 1"):
            parse("ticket_id,text\nT1,a\nT2,b\n", max_rows=1)

    def test_non_utf8_rejected(self) -> None:
        with pytest.raises(CSVFormatError):
            decode_csv_bytes("ticket_id,text\nT1,caf\xe9\n".encode("latin-1"))

    def test_oversized_field_is_format_error_not_crash(self) -> None:
        with pytest.raises(CSVFormatError, match="could not be parsed"):
            parse("ticket_id,text\nT1," + "x" * 200_000 + "\n")
