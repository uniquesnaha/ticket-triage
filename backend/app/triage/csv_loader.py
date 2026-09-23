"""CSV → tickets, shared by the upload endpoint and the CLI.

Missing or oversized fields never fail the whole file: each row becomes a ticket, and
problems are recorded as InputWarnings so the pipeline can handle them deterministically.
Only structural problems (no header, missing columns, malformed IDs) are hard errors.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.core.schema import TICKET_ID_PATTERN, InputWarning, TicketInput

REQUIRED_COLUMNS = frozenset({"ticket_id", "text"})
MAX_TICKET_ID_LENGTH = 50


class CSVFormatError(ValueError):
    """The CSV cannot be interpreted as a ticket file."""


@dataclass
class ParsedTicket:
    ticket: TicketInput
    warnings: list[InputWarning] = field(default_factory=list)


def parse_tickets_csv(
    content: str,
    *,
    max_text_length: int,
    max_rows: int | None = None,
) -> list[ParsedTicket]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise CSVFormatError("CSV has no header row")

    # Normalise headers so "Ticket_ID " and "ticket_id" are treated the same.
    reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]
    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise CSVFormatError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    try:
        return _parse_rows(reader, max_text_length=max_text_length, max_rows=max_rows)
    except csv.Error as exc:  # e.g. a field larger than csv.field_size_limit()
        raise CSVFormatError(f"CSV could not be parsed: {exc}") from exc


def _parse_rows(
    reader: csv.DictReader[str], *, max_text_length: int, max_rows: int | None
) -> list[ParsedTicket]:
    parsed: list[ParsedTicket] = []
    seen_ids: set[str] = set()

    for row_number, row in enumerate(reader, start=1):
        if max_rows is not None and row_number > max_rows:
            raise CSVFormatError(f"CSV exceeds the maximum of {max_rows} tickets per batch")

        warnings: list[InputWarning] = []
        ticket_id = (row.get("ticket_id") or "").strip()
        text = (row.get("text") or "").strip()

        if not ticket_id:
            ticket_id = f"ROW-{row_number}"
            warnings.append(InputWarning.MISSING_TICKET_ID)
        elif len(ticket_id) > MAX_TICKET_ID_LENGTH or not TICKET_ID_PATTERN.match(ticket_id):
            raise CSVFormatError(
                f"Row {row_number}: ticket_id must be at most {MAX_TICKET_ID_LENGTH} characters "
                "of letters, digits, '-', '_' or '.'"
            )

        if ticket_id in seen_ids:
            warnings.append(InputWarning.DUPLICATE_TICKET_ID)
        seen_ids.add(ticket_id)

        if not text:
            warnings.append(InputWarning.MISSING_TEXT)
        elif len(text) > max_text_length:
            text = text[:max_text_length]
            warnings.append(InputWarning.TEXT_TRUNCATED)

        try:
            ticket = TicketInput(ticket_id=ticket_id, text=text)
        except ValidationError as exc:  # pragma: no cover — guarded by checks above
            raise CSVFormatError(f"Row {row_number} is invalid: {exc}") from exc
        parsed.append(ParsedTicket(ticket=ticket, warnings=warnings))

    if not parsed:
        raise CSVFormatError("CSV contains no ticket rows")
    return parsed


def decode_csv_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")  # tolerate a UTF-8 BOM (Excel exports)
    except UnicodeDecodeError as exc:
        raise CSVFormatError("CSV must be UTF-8 encoded") from exc
