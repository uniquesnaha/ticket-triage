"""X-API-Key authentication dependency."""

from __future__ import annotations

import hmac

import structlog
from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(x_api_key: str | None = Security(api_key_header)) -> str:
    """Validate the X-API-Key header with a timing-safe comparison."""
    if not x_api_key:
        logger.warning("auth_failed", reason="missing_api_key")
        raise AuthenticationError("X-API-Key header is required")

    expected = get_settings().triage_api_key.get_secret_value().encode()
    if not hmac.compare_digest(expected, x_api_key.encode()):
        logger.warning("auth_failed", reason="invalid_api_key")
        raise AuthenticationError("Invalid API key")

    return x_api_key
