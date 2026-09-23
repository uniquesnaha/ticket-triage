"""FastAPI route handlers for /api/v1/triage."""

import csv
import io
import time
from collections import Counter


import structlog
from fastapi import APIRouter, Depends, File, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, InvalidCSVError
from app.core.schema import (
    TicketInput,
    TriageBatchRequest,
    TriageBatchResponse,
)
from app.security.auth import require_api_key
from app.triage.pipeline import process_batch

router = APIRouter()
logger = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)

REQUIRED_CSV_COLUMNS = {"ticket_id", "text"}


def _build_response(results: list, elapsed_ms: int) -> TriageBatchResponse:
    settings = get_settings()
    category_counts = Counter(r.category.value for r in results)
    priority_counts = Counter(r.priority.value for r in results)
    return TriageBatchResponse(
        results=results,
        total=len(results),
        processing_time_ms=elapsed_ms,
        needs_human_review_count=sum(1 for r in results if r.needs_human_review),
        by_category=dict(category_counts),
        by_priority=dict(priority_counts),
        model=settings.model_name,
    )


@router.post(
    "/triage",
    response_model=TriageBatchResponse,
    summary="Triage a batch of support tickets (JSON)",
    description="Accept up to 50 tickets as JSON and return structured triage results.",
)
@limiter.limit("30/minute")
async def triage_json(
    request: Request,
    body: TriageBatchRequest,
    _auth: str = Depends(require_api_key),
) -> TriageBatchResponse:
    start = time.monotonic()
    log = logger.bind(batch_size=len(body.tickets))
    log.info("triage_batch_start")

    settings = get_settings()
    results = await process_batch(body.tickets, settings.model_name)
    elapsed = int((time.monotonic() - start) * 1000)

    log.info("triage_batch_complete", elapsed_ms=elapsed, total=len(results))
    return _build_response(results, elapsed)


@router.post(
    "/triage/upload",
    response_model=TriageBatchResponse,
    summary="Triage tickets via CSV file upload",
    description="Upload a CSV file with 'ticket_id' and 'text' columns.",
)
@limiter.limit("5/minute")
async def triage_upload(
    request: Request,
    file: UploadFile = File(...),
    _auth: str = Depends(require_api_key),
) -> TriageBatchResponse:
    start = time.monotonic()
    settings = get_settings()

    # Validate MIME type
    if file.content_type not in ("text/csv", "application/csv", "text/plain", "application/octet-stream"):
        raise InvalidCSVError("File must be a CSV (text/csv). Detected: " + (file.content_type or "unknown"))

    # Read and size-check
    content = await file.read()
    max_bytes = settings.max_csv_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileTooLargeError(settings.max_csv_size_mb)

    # Decode and parse
    try:
        text_content = content.decode("utf-8-sig")  # handles BOM
    except UnicodeDecodeError:
        raise InvalidCSVError("CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text_content))

    if not reader.fieldnames:
        raise InvalidCSVError("CSV has no headers")

    actual_columns = {col.strip().lower() for col in reader.fieldnames}
    missing = REQUIRED_CSV_COLUMNS - actual_columns
    if missing:
        raise InvalidCSVError(f"CSV is missing required columns: {missing}")

    tickets: list[TicketInput] = []
    for i, row in enumerate(reader):
        try:
            ticket = TicketInput(
                ticket_id=str(row.get("ticket_id", "")).strip(),
                text=str(row.get("text", "")).strip(),
            )
            tickets.append(ticket)
        except Exception as e:
            raise InvalidCSVError(f"Row {i + 2} is invalid: {e}") from e

        if len(tickets) > settings.max_tickets_per_batch:
            raise InvalidCSVError(
                f"CSV exceeds maximum of {settings.max_tickets_per_batch} tickets per batch"
            )

    if not tickets:
        raise InvalidCSVError("CSV contains no ticket rows")

    logger.info("csv_upload_parsed", ticket_count=len(tickets), filename=file.filename)

    results = await process_batch(tickets, settings.model_name)
    elapsed = int((time.monotonic() - start) * 1000)

    return _build_response(results, elapsed)
