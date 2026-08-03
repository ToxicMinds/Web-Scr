"""Structured logging setup using structlog.

A single :func:`configure_logging` call wires structlog to emit either JSON
(for CI/production log aggregation) or a human-friendly console renderer (for
local development), controlled by :class:`Settings`.
"""

from __future__ import annotations

import logging
import sys
from typing import TextIO

import structlog

from supplement_optimizer.config.settings import Settings, get_settings


class _LiveStderr:
    """Stream proxy that always forwards to the *current* ``sys.stderr``.

    ``structlog.PrintLoggerFactory`` binds to a concrete stream object at
    configuration time. Under test runners (e.g. Typer's ``CliRunner``) the
    real ``sys.stderr`` is temporarily swapped for a capture buffer that is
    later closed, which would otherwise leave a cached logger writing to a
    dead stream. Forwarding lazily keeps logging robust across stream swaps.
    """

    def write(self, data: str) -> int:
        return sys.stderr.write(data)

    def flush(self) -> None:
        sys.stderr.flush()


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog + stdlib logging. Idempotent."""
    settings = settings or get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level)

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

    stream: TextIO = _LiveStderr()  # type: ignore[assignment]
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=stream),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
