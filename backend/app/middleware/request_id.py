"""FastAPI middleware: inject X-Request-ID into every request/response."""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID into every request and response for tracing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Only echo well-formed client IDs; anything else could be log/header injection.
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _SAFE_ID.fullmatch(incoming) else str(uuid.uuid4())

        # Bind to structlog context so all log lines in this request include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
