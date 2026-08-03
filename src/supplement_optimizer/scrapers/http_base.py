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

from abc import abstractmethod

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


class HttpScraperPlugin(FixtureScraperPlugin):
    """Base for server-rendered retailers scraped over HTTP.

    Inherits retailer/shipping/coupon declaration from
    :class:`FixtureScraperPlugin` (so metadata stays declarative) but overrides
    :meth:`fetch` to retrieve and parse live listing pages. Subclasses implement
    :meth:`listing_urls` and :meth:`parse`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @abstractmethod
    def listing_urls(self, category: str) -> list[str]:
        """Return the listing page URL(s) to scrape for ``category``."""

    @abstractmethod
    def parse(self, category: str, soup: BeautifulSoup, source_url: str) -> list[Offer]:
        """Parse one listing page into raw :class:`Offer` objects."""

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
        offers: list[Offer] = []
        headers = {"User-Agent": self._settings.scraper_user_agent}
        timeout = self._settings.scraper_request_timeout_seconds
        async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as c:
            for url in self.listing_urls(category):
                try:
                    html = await self._get(c, url)
                except httpx.HTTPError as exc:
                    _logger.warning("fetch_failed", url=url, error=str(exc))
                    continue
                soup = BeautifulSoup(html, "lxml")
                offers.extend(self.parse(category, soup, url))
        return offers
