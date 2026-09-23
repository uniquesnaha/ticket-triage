"""Structured JSON logging via structlog."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

import structlog

from app.core.config import get_settings


def configure_logging(stream: TextIO = sys.stdout) -> None:
    """Configure structlog. JSON in production (for log drains), pretty console otherwise."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON output for log aggregators (Datadog, CloudWatch, etc.)
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty console output for development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=stream.isatty()),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=stream),
        cache_logger_on_first_use=False,
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
