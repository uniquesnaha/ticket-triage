"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.schema import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service status and configuration metadata.",
    include_in_schema=True,
)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        model=settings.model_name,
        version=settings.app_version,
        docs_enabled=settings.docs_enabled,
    )
