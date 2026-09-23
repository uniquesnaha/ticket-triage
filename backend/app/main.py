"""FastAPI application entrypoint — wires middleware, routes, and error handlers.

The API only serves /api/*. The React frontend is static and is served by Vercel
(or by Vite in local development), not by this process.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.v1.health import router as health_router
from app.api.v1.triage import router as triage_router
from app.core.config import get_settings
from app.core.exceptions import (
    TriageAPIError,
    generic_exception_handler,
    rate_limit_exception_handler,
    triage_api_exception_handler,
)
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger = structlog.get_logger()
    logger.info("startup", environment=settings.environment, model=settings.model_name)
    if not settings.llm_configured:
        logger.error("startup_llm_not_configured", hint="Set GROQ_API_KEY")
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    # Configure logging here rather than in lifespan: serverless runtimes may not
    # run lifespan events.
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Ticket Triage API",
        description="Ticket triage: structured LLM output + deterministic guardrails.",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if settings.docs_enabled else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(TriageAPIError, triage_api_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Middleware runs outermost-first in reverse registration order.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(triage_router, prefix=API_PREFIX, tags=["Triage"])
    app.include_router(health_router, prefix=API_PREFIX, tags=["Health"])
    return app


app = create_app()
