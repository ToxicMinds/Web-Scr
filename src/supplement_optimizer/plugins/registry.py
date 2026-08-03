"""Plugin registry + factory (Factory pattern).

Scraper plugins register themselves (via :func:`register` or the
``@register`` decorator). :class:`PluginRegistry` then constructs them on demand
by slug, enabling configuration-driven selection of retailers in the CLI/CI.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable

from supplement_optimizer.config.logging import get_logger
from supplement_optimizer.plugins.base import ScraperPlugin

_logger = get_logger(__name__)

# Global class registry: slug -> plugin class.
_REGISTRY: dict[str, type[ScraperPlugin]] = {}


def register(plugin_cls: type[ScraperPlugin]) -> type[ScraperPlugin]:
    """Class decorator that registers a scraper plugin by its ``slug``."""
    slug = getattr(plugin_cls, "slug", None)
    if not slug:
        msg = f"{plugin_cls.__name__} must define a non-empty 'slug'"
        raise ValueError(msg)
    if slug in _REGISTRY and _REGISTRY[slug] is not plugin_cls:
        msg = f"Duplicate plugin slug '{slug}'"
        raise ValueError(msg)
    _REGISTRY[slug] = plugin_cls
    return plugin_cls


class PluginRegistry:
    """Discovers and instantiates registered scraper plugins."""

    def __init__(self, scrapers_package: str = "supplement_optimizer.scrapers") -> None:
        self._package = scrapers_package
        self._discovered = False

    def discover(self) -> None:
        """Import every module under the scrapers package to trigger registration."""
        if self._discovered:
            return
        package = importlib.import_module(self._package)
        for module in pkgutil.walk_packages(package.__path__, prefix=f"{self._package}."):
            importlib.import_module(module.name)
        self._discovered = True
        _logger.info("plugins_discovered", count=len(_REGISTRY), slugs=sorted(_REGISTRY))

    def slugs(self) -> list[str]:
        """Return all registered plugin slugs (after discovery)."""
        self.discover()
        return sorted(_REGISTRY)

    def create(self, slug: str) -> ScraperPlugin:
        """Instantiate the plugin registered under ``slug``."""
        self.discover()
        try:
            return _REGISTRY[slug]()
        except KeyError as exc:
            msg = f"No scraper plugin registered for slug '{slug}'"
            raise KeyError(msg) from exc

    def create_all(self, slugs: Iterable[str] | None = None) -> list[ScraperPlugin]:
        """Instantiate all plugins, or just those named in ``slugs``."""
        self.discover()
        chosen = list(slugs) if slugs is not None else sorted(_REGISTRY)
        return [self.create(slug) for slug in chosen]

    def live_slugs(self) -> list[str]:
        """Return slugs of plugins that have a real live-scraping implementation.

        Used by reporting so a fixture/seed retailer is never published as live,
        verified market data (see ``FixtureScraperPlugin.LIVE``).
        """
        self.discover()
        return sorted(slug for slug, cls in _REGISTRY.items() if getattr(cls, "LIVE", False))
