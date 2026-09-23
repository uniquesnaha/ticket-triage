"""FastAPI route handlers for /api/v1/triage."""
# No `from __future__ import annotations`: slowapi wraps the handlers, and FastAPI
# must resolve their real annotation objects to build request models.

import time
from collections import Counter

import structlog
from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, InvalidCSVError
from app.core.rate_limit import limiter
from app.core.schema import TriageBatchRequest, TriageBatchResponse, TriageResult
from app.security.auth import require_api_key
from app.triage.csv_loader import CSVFormatError, decode_csv_bytes, parse_tickets_csv
from app.triage.pipeline import process_batch

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = structlog.get_logger()

ALLOWED_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",  # what Windows browsers report for .csv
    "text/plain",
    "application/octet-stream",
}


def _build_response(results: list[TriageResult], elapsed_ms: int) -> TriageBatchResponse:
    return TriageBatchResponse(
        results=results,
        total=len(results),
        processing_time_ms=elapsed_ms,
        needs_human_review_count=sum(1 for r in results if r.needs_human_review),
        by_category=dict(Counter(r.category.value for r in results)),
        by_priority=dict(Counter(r.priority.value for r in results)),
        model=get_settings().model_name,
    )


@router.post(
    "/triage",
    response_model=TriageBatchResponse,
    summary="Triage a batch of support tickets (JSON)",
)
@limiter.limit(lambda: get_settings().rate_limit_triage)
async def triage_json(request: Request, body: TriageBatchRequest) -> TriageBatchResponse:
    start = time.monotonic()
    settings = get_settings()
    logger.info("triage_batch_start", batch_size=len(body.tickets))

    results = await process_batch(body.tickets, settings.model_name, timeout=settings.batch_timeout)
    elapsed = int((time.monotonic() - start) * 1000)
    logger.info("triage_batch_complete", elapsed_ms=elapsed, total=len(results))
    return _build_response(results, elapsed)


@router.post(
    "/triage/upload",
    response_model=TriageBatchResponse,
    summary="Triage tickets via CSV upload (columns: ticket_id, text)",
)
@limiter.limit(lambda: get_settings().rate_limit_upload)
async def triage_upload(request: Request, file: UploadFile = File(...)) -> TriageBatchResponse:
    start = time.monotonic()
    settings = get_settings()

    if file.content_type not in ALLOWED_CSV_CONTENT_TYPES:
        raise InvalidCSVError(f"File must be a CSV. Detected: {file.content_type or 'unknown'}")

    max_bytes = settings.max_csv_size_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise FileTooLargeError(settings.max_csv_size_mb)

    try:
        parsed = parse_tickets_csv(
            decode_csv_bytes(content),
            max_text_length=settings.max_ticket_length,
            max_rows=settings.max_tickets_per_batch,
        )
    except CSVFormatError as exc:
        raise InvalidCSVError(str(exc)) from exc

    logger.info("csv_upload_parsed", ticket_count=len(parsed))
    results = await process_batch(
        [p.ticket for p in parsed],
        settings.model_name,
        input_warnings=[p.warnings for p in parsed],
        timeout=settings.batch_timeout,
    )
    return _build_response(results, int((time.monotonic() - start) * 1000))
