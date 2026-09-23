"""FastAPI application entrypoint — wires all middleware, routes, and handlers."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
    # Fallback routes without /api in case reverse proxy or serverless strips /api
    app.include_router(triage_router, prefix="/v1", tags=["Triage"], include_in_schema=False)
    app.include_router(health_router, prefix="/v1", tags=["Health"], include_in_schema=False)

    # ── Static Frontend Serving ───────────────────────────────────────────────
    dist_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")),
        os.path.abspath(os.path.join(os.getcwd(), "frontend", "dist")),
    ]
    dist_dir = next((d for d in dist_candidates if os.path.exists(d)), None)

    if dist_dir:
        assets_dir = os.path.join(dist_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/project_1.csv", include_in_schema=False)
        async def sample_csv():
            csv_file = os.path.join(dist_dir, "project_1.csv")
            if os.path.exists(csv_file):
                return FileResponse(csv_file, media_type="text/csv")
            return HTTPException(status_code=404, detail="File not found")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("v1/"):
                raise HTTPException(status_code=404, detail="Not Found")
            index_path = os.path.join(dist_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="Frontend build not found")

    return app


app = create_app()
