"""FastAPI application entrypoint — wires all middleware, routes, and handlers."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.health import router as health_router
from app.api.v1.triage import router as triage_router
from app.core.config import get_settings
from app.core.exceptions import (
    TriageAPIError,
    generic_exception_handler,
    triage_api_exception_handler,
)
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    configure_logging()
    logger = structlog.get_logger()
    settings = get_settings()
    logger.info(
        "startup",
        environment=settings.environment,
        model=settings.model_name,
        docs=settings.docs_enabled,
    )
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Ticket Triage API",
        description="AI-powered support ticket triage with deterministic guardrails.",
        version=settings.app_version,
        lifespan=lifespan,
        # Disable docs in production
        docs_url="/api/v1/docs" if settings.docs_enabled else None,
        redoc_url="/api/v1/redoc" if settings.docs_enabled else None,
        openapi_url="/api/v1/openapi.json" if settings.docs_enabled else None,
    )

    # ── Rate limiter ──────────────────────────────────────────────────────────
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # ── Middleware (applied in reverse registration order) ────────────────────
    # 1. Security headers (outermost)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. Request ID tracing
    app.add_middleware(RequestIDMiddleware)

    # 3. Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    # 4. CORS (innermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(TriageAPIError, triage_api_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(triage_router, prefix="/api/v1", tags=["Triage"])
    app.include_router(health_router, prefix="/api/v1", tags=["Health"])

    return app


app = create_app()
