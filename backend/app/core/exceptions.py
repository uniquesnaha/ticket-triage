"""Custom HTTP exceptions with RFC 7807 Problem Details format."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class TriageAPIError(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        error_type: str = "https://ticket-triage.api/errors/generic",
    ) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.error_type = error_type
        super().__init__(detail)


class AuthenticationError(TriageAPIError):
    def __init__(self, detail: str = "Invalid or missing API key") -> None:
        super().__init__(
            status_code=401,
            title="Unauthorized",
            detail=detail,
            error_type="https://ticket-triage.api/errors/unauthorized",
        )


class RateLimitError(TriageAPIError):
    def __init__(self) -> None:
        super().__init__(
            status_code=429,
            title="Too Many Requests",
            detail="Rate limit exceeded. Please slow down your requests.",
            error_type="https://ticket-triage.api/errors/rate-limit",
        )


class ValidationError(TriageAPIError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=422,
            title="Validation Error",
            detail=detail,
            error_type="https://ticket-triage.api/errors/validation",
        )


class FileTooLargeError(TriageAPIError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            status_code=413,
            title="File Too Large",
            detail=f"CSV file exceeds the maximum allowed size of {max_mb} MB.",
            error_type="https://ticket-triage.api/errors/file-too-large",
        )


class InvalidCSVError(TriageAPIError):
    def __init__(self, detail: str = "CSV is malformed or missing required columns") -> None:
        super().__init__(
            status_code=400,
            title="Invalid CSV",
            detail=detail,
            error_type="https://ticket-triage.api/errors/invalid-csv",
        )


# ── Exception Handlers ────────────────────────────────────────────────────────


async def triage_api_exception_handler(request: Request, exc: TriageAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": exc.error_type,
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://ticket-triage.api/errors/internal",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred. Please try again or contact support.",
            "instance": str(request.url),
        },
    )
