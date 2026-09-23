"""Health check endpoint (public)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.schema import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        # "degraded": the API is up but every ticket would fall back to manual review.
        status="ok" if settings.llm_configured else "degraded",
        environment=settings.environment,
        model=settings.model_name,
        version=settings.app_version,
        llm_configured=settings.llm_configured,
    )
