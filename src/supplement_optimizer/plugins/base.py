"""Scraper plugin contract (Plugin pattern).

Every retailer is an independent plugin implementing :class:`ScraperPlugin`.
Adding a retailer means writing one new subclass and registering it -- no other
code changes. The base class also applies the relevant :class:`ProductFilter`
automatically, so concrete plugins only worry about *extraction*.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from supplement_optimizer.domain.models import Coupon, Offer, Retailer, ShippingRule
from supplement_optimizer.plugins.filters import filter_for


class ScrapeResult(BaseModel):
    """Outcome of scraping one category from one retailer."""

    retailer_slug: str
    category: str
    offers: tuple[Offer, ...]
    raw_count: int
    errors: tuple[str, ...] = ()

    @property
    def accepted_count(self) -> int:
        """Number of offers that passed the product filter."""
        return len(self.offers)


class ScraperPlugin(ABC):
    """Base class for all retailer scrapers.

    Subclasses declare a unique :attr:`slug`, describe their retailer/shipping/
    coupons, and implement :meth:`fetch` for each supported category. The base
    class handles filtering so category rules are never duplicated per plugin.
    """

    #: Stable, unique identifier. Must match the retailer slug.
    slug: ClassVar[str]

    @abstractmethod
    def retailer(self) -> Retailer:
        """Return the :class:`Retailer` this plugin represents."""

    def shipping_rules(self) -> list[ShippingRule]:
        """Return known shipping rules (default: none)."""
        return []

    def coupons(self) -> list[Coupon]:
        """Return known active coupons (default: none)."""
        return []

    @abstractmethod
    def supported_categories(self) -> tuple[str, ...]:
        """Return the category keys this plugin can scrape."""

    @abstractmethod
    async def fetch(self, category: str) -> list[Offer]:
        """Extract *raw* offers for ``category`` (no filtering)."""

    async def scrape(self, category: str) -> ScrapeResult:
        """Fetch then filter offers for ``category``.

        The applicable :class:`ProductFilter` (if any) enforces the category's
        inclusion rules; unknown categories pass through unfiltered.
        """
        raw = await self.fetch(category)
        product_filter = filter_for(category)
        offers = product_filter.apply(raw) if product_filter else list(raw)
        return ScrapeResult(
            retailer_slug=self.slug,
            category=category,
            offers=tuple(offers),
            raw_count=len(raw),
        )
