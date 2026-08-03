"""Prom-IN scraper plugin (Czechia, CZK).

Added purely to demonstrate **Tier 1** extensibility: a brand-new retailer is a
single self-contained file that subclasses :class:`FixtureScraperPlugin` and is
registered with ``@register`` -- nothing else in the codebase changes. It prices
in CZK, exercising the optimizer's currency conversion, and also carries
**Tier 2** ``omega_3`` offers to show a new divisible ingredient needs only a
catalog entry once its filter + category exist.
"""

from __future__ import annotations

from supplement_optimizer.domain.enums import CouponType, CreatineForm, Currency, ProductCategory
from supplement_optimizer.plugins.registry import register
from supplement_optimizer.scrapers._fixture import (
    CouponSpec,
    FixtureScraperPlugin,
    OfferSpec,
    RetailerSpec,
    ShippingSpec,
)
from supplement_optimizer.scrapers.constants import EU_SHIPS

WHEY = ProductCategory.WHEY_PROTEIN.value
CREATINE = ProductCategory.CREATINE_MONOHYDRATE.value
OMEGA3 = ProductCategory.OMEGA_3.value


@register
class PromInPlugin(FixtureScraperPlugin):
    """Prom-IN -- Czech manufacturer/retailer, prices in CZK."""

    RETAILER = RetailerSpec(
        slug="prom_in",
        name="Prom-IN",
        base_url="https://prom-in.cz",
        home_country="CZ",
        currency=Currency.CZK,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="120", free_over="1500", min_days=2, max_days=4, methods=("courier",)
        ),
        ShippingSpec(
            "CZ", cost="79", free_over="1000", min_days=1, max_days=2, methods=("courier",)
        ),
    )
    COUPONS = (CouponSpec("PROMIN10", CouponType.PERCENT, value="0.10", min_subtotal="1000"),)
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Prom-IN Essential Whey 1000 g",
                1000,
                "599",
                "/essential-whey-1000g",
                protein_pct="73",
                serving_size_g="30",
                protein_per_serving_g="22",
                flavours=("chocolate", "strawberry"),
            ),
            OfferSpec(
                "Prom-IN Essential Whey 2250 g",
                2250,
                "1249",
                "/essential-whey-2250g",
                protein_pct="73",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Prom-IN Creatine Monohydrate 500 g",
                500,
                "359",
                "/creatine-monohydrate-500g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
        OMEGA3: (
            OfferSpec(
                "Prom-IN Omega-3 Fish Oil 250 g",
                250,
                "329",
                "/omega-3-fish-oil-250g",
            ),
            OfferSpec(
                "Prom-IN Omega-3 Fish Oil 500 g",
                500,
                "579",
                "/omega-3-fish-oil-500g",
            ),
        ),
    }
