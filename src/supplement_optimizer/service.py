"""Application service: orchestrates scraping -> optimization -> normalization.

This is the use-case layer that wires the plugin registry, the optimization
engine and the normalizer together. It contains no business rules itself -- it
coordinates the pieces (Clean Architecture: interactors depend on abstractions).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import polars as pl

from supplement_optimizer.config.logging import get_logger
from supplement_optimizer.domain.models import (
    BasketRequest,
    Coupon,
    Offer,
    Retailer,
    ShippingRule,
)
from supplement_optimizer.normalization import to_frame
from supplement_optimizer.optimizer import OptimizationEngine, RateProvider, Solution
from supplement_optimizer.optimizer.rates import default_rate_provider
from supplement_optimizer.plugins.base import ScrapeResult
from supplement_optimizer.plugins.registry import PluginRegistry

_logger = get_logger(__name__)


@dataclass
class MarketData:
    """Everything scraped from the market for a set of categories."""

    offers: list[Offer] = field(default_factory=list)
    retailers: dict[str, Retailer] = field(default_factory=dict)
    shipping_rules: dict[tuple[str, str], ShippingRule] = field(default_factory=dict)
    coupons: dict[str, list[Coupon]] = field(default_factory=dict)
    scrape_results: list[ScrapeResult] = field(default_factory=list)


@dataclass
class RunResult:
    """The full output of one optimization run."""

    request: BasketRequest
    market: MarketData
    solution: Solution | None
    metrics: pl.DataFrame


class OptimizationService:
    """Coordinates the scrape -> optimize -> normalize pipeline."""

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        rate_provider: RateProvider | None = None,
    ) -> None:
        self._registry = registry or PluginRegistry()
        self._rates = rate_provider or default_rate_provider()

    async def gather_market_data(
        self, categories: list[str], *, retailer_slugs: list[str] | None = None
    ) -> MarketData:
        """Scrape ``categories`` from selected (or all) retailer plugins."""
        plugins = self._registry.create_all(retailer_slugs)
        market = MarketData()

        for plugin in plugins:
            retailer = plugin.retailer()
            market.retailers[retailer.slug] = retailer
            for rule in plugin.shipping_rules():
                market.shipping_rules[rule.retailer_slug, rule.destination_country] = rule
            coupons = plugin.coupons()
            if coupons:
                market.coupons[retailer.slug] = coupons

        # Scrape every (plugin, category) pair concurrently.
        tasks = [
            plugin.scrape(category)
            for plugin in plugins
            for category in categories
            if category in plugin.supported_categories()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                _logger.warning("scrape_error", error=str(result))
                continue
            market.scrape_results.append(result)
            market.offers.extend(result.offers)

        _logger.info(
            "market_gathered",
            retailers=len(market.retailers),
            offers=len(market.offers),
            categories=categories,
        )
        return market

    def build_engine(self, market: MarketData) -> OptimizationEngine:
        """Construct an :class:`OptimizationEngine` from gathered market data."""
        return OptimizationEngine(
            retailers=market.retailers,
            shipping_rules=market.shipping_rules,
            coupons=market.coupons,
            rate_provider=self._rates,
        )

    async def run(
        self, request: BasketRequest, *, retailer_slugs: list[str] | None = None
    ) -> RunResult:
        """Execute the full pipeline for ``request`` and return the result."""
        categories = [r.category for r in request.requirements]
        market = await self.gather_market_data(categories, retailer_slugs=retailer_slugs)
        engine = self.build_engine(market)
        solution = engine.optimize(request, market.offers)
        metrics = to_frame(market.offers)
        return RunResult(request=request, market=market, solution=solution, metrics=metrics)
