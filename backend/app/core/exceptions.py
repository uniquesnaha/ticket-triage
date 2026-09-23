"""API errors rendered as RFC 7807 Problem Details."""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = structlog.get_logger()

_ERROR_BASE = "https://ticket-triage.api/errors"


class TriageAPIError(Exception):
    def __init__(self, status_code: int, title: str, detail: str, error_type: str) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.error_type = f"{_ERROR_BASE}/{error_type}"
        super().__init__(detail)


class AuthenticationError(TriageAPIError):
    def __init__(self, detail: str = "Invalid or missing API key") -> None:
        super().__init__(401, "Unauthorized", detail, "unauthorized")


class FileTooLargeError(TriageAPIError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            413,
            "File Too Large",
            f"CSV file exceeds the maximum allowed size of {max_mb} MB.",
            "file-too-large",
        )


class InvalidCSVError(TriageAPIError):
    def __init__(self, detail: str = "CSV is malformed or missing required columns") -> None:
        super().__init__(400, "Invalid CSV", detail, "invalid-csv")


def _problem(
    request: Request,
    status: int,
    title: str,
    detail: str,
    error_type: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
        content={
            "type": error_type,
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
        },
    )


async def triage_api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, TriageAPIError)
    return _problem(request, exc.status_code, exc.title, exc.detail, exc.error_type)


async def rate_limit_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)
    return _problem(
        request,
        429,
        "Too Many Requests",
        f"Rate limit exceeded ({exc.detail}). Please slow down.",
        f"{_ERROR_BASE}/rate-limit",
        headers={"Retry-After": "60"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path, error_type=type(exc).__name__)
    return _problem(
        request,
        500,
        "Internal Server Error",
        "An unexpected error occurred. Please try again or contact support.",
        f"{_ERROR_BASE}/internal",
    )
