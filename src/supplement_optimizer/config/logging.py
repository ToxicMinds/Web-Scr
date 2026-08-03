"""Structured logging setup using structlog.

A single :func:`configure_logging` call wires structlog to emit either JSON
(for CI/production log aggregation) or a human-friendly console renderer (for
local development), controlled by :class:`Settings`.
"""

from __future__ import annotations

import logging
import sys

import structlog

from supplement_optimizer.config.settings import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog + stdlib logging. Idempotent."""
    settings = settings or get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
