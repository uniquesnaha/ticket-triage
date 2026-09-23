"""FastAPI middleware: inject X-Request-ID into every request/response."""
from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID into every request and response for tracing."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context so all log lines in this request include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-ID"] = request_id
        return response
