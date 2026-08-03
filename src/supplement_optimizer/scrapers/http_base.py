"""HTTP scraping base for live retailers (httpx + BeautifulSoup + tenacity).

Retailers whose listings are server-rendered can be scraped without a browser.
:class:`HttpScraperPlugin` provides a resilient, rate-limited fetch with retries
and leaves HTML parsing to subclasses via :meth:`parse`. Retailers requiring a
real browser (JS-rendered listings) should instead subclass a Playwright base
(see ``docs/PLUGIN_GUIDE.md``); the choice per retailer is recorded in the ADR
log so the httpx-vs-Playwright decision is never re-litigated blindly.

These live plugins are opt-in: the default pipeline uses the deterministic
fixture catalogs so tests and CI never depend on third-party site availability.
"""

from __future__ import annotations

import os
from abc import abstractmethod
from collections.abc import Callable
from typing import ClassVar

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from supplement_optimizer.config.logging import get_logger
from supplement_optimizer.config.settings import Settings, get_settings
from supplement_optimizer.domain.models import Offer
from supplement_optimizer.scrapers._fixture import FixtureScraperPlugin

_logger = get_logger(__name__)

ClientFactory = Callable[[], httpx.AsyncClient]


class HttpScraperPlugin(FixtureScraperPlugin):
    """Base for server-rendered retailers scraped over HTTP.

    Inherits retailer/shipping/coupon declaration from
    :class:`FixtureScraperPlugin` (so metadata stays declarative) but overrides
    :meth:`fetch` to retrieve and parse live listing pages. Subclasses implement
    :meth:`listing_urls` and :meth:`parse`.

    Like the Magento base, live scraping is opt-in: unless ``scraper_live`` is
    enabled (or an ``httpx`` client is injected for deterministic parser tests)
    the deterministic fixture catalog is used, so CI never depends on a third
    party being reachable.
    """

    LIVE: ClassVar[bool] = True

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client_factory = client_factory

    @abstractmethod
    def listing_urls(self, category: str) -> list[str]:
        """Return the listing page URL(s) to scrape for ``category``."""

    @abstractmethod
    def parse(self, category: str, soup: BeautifulSoup, source_url: str) -> list[Offer]:
        """Parse one listing page into raw :class:`Offer` objects."""

    def _make_client(self) -> httpx.AsyncClient:
        if self._client_factory is not None:
            return self._client_factory()
        headers = {"User-Agent": self._settings.scraper_user_agent}
        return httpx.AsyncClient(
            headers=headers,
            timeout=self._settings.scraper_request_timeout_seconds,
            follow_redirects=True,
            verify=self._verify(),
        )

    def _verify(self) -> str | bool:
        """Resolve the TLS trust store (see :meth:`MagentoGraphQLScraper._verify`)."""
        bundle = self._settings.scraper_ca_bundle or os.environ.get("SSL_CERT_FILE")
        return bundle if bundle else True

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    async def _get(self, client: httpx.AsyncClient, url: str) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    async def fetch(self, category: str) -> list[Offer]:
        # Offline/deterministic mode (tests, CI, local default): use the seed
        # catalog. Live scraping only when explicitly enabled or a client is
        # injected (parser tests via MockTransport). Mirrors the Magento base.
        if self._client_factory is None and not self._settings.scraper_live:
            return await FixtureScraperPlugin.fetch(self, category)
        offers: list[Offer] = []
        async with self._make_client() as c:
            for url in self.listing_urls(category):
                try:
                    html = await self._get(c, url)
                except httpx.HTTPError as exc:
                    _logger.warning("fetch_failed", url=url, error=str(exc))
                    continue
                soup = BeautifulSoup(html, "lxml")
                offers.extend(self.parse(category, soup, url))
        return offers
