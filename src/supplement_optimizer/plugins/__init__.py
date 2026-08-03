"""Plugin contracts, registry and product filters."""

from __future__ import annotations

from supplement_optimizer.plugins.base import ScrapeResult, ScraperPlugin
from supplement_optimizer.plugins.filters import (
    CreatineMonohydrateFilter,
    ProductFilter,
    WheyProteinFilter,
    filter_for,
)
from supplement_optimizer.plugins.registry import PluginRegistry, register

__all__ = [
    "CreatineMonohydrateFilter",
    "PluginRegistry",
    "ProductFilter",
    "ScrapeResult",
    "ScraperPlugin",
    "WheyProteinFilter",
    "filter_for",
    "register",
]
