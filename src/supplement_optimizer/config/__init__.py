"""Configuration and cross-cutting concerns (settings, logging)."""

from __future__ import annotations

from supplement_optimizer.config.logging import configure_logging, get_logger
from supplement_optimizer.config.settings import Settings, get_settings

__all__ = ["Settings", "configure_logging", "get_logger", "get_settings"]
