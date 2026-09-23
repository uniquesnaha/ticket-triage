"""X-API-Key authentication dependency."""
from __future__ import annotations

import hmac

import structlog
from fastapi import Header
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """FastAPI dependency — validates X-API-Key header using timing-safe comparison."""
    settings = get_settings()

    if not x_api_key:
        logger.warning("auth_failed", reason="missing_api_key")
        raise AuthenticationError("X-API-Key header is required")

    # Timing-safe comparison to prevent timing attacks
    expected = settings.triage_api_key.encode()
    provided = x_api_key.encode()

    if not hmac.compare_digest(expected, provided):
        logger.warning("auth_failed", reason="invalid_api_key")
        raise AuthenticationError("Invalid API key")

    return x_api_key
