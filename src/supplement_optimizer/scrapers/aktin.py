"""Aktin scraper plugin (Slovakia/Czechia, EUR)."""

from __future__ import annotations

from supplement_optimizer.domain.enums import CreatineForm, Currency, ProductCategory
from supplement_optimizer.plugins.registry import register
from supplement_optimizer.scrapers._fixture import (
    FixtureScraperPlugin,
    OfferSpec,
    RetailerSpec,
    ShippingSpec,
)
from supplement_optimizer.scrapers.constants import EU_SHIPS

WHEY = ProductCategory.WHEY_PROTEIN.value
CREATINE = ProductCategory.CREATINE_MONOHYDRATE.value


@register
class AktinPlugin(FixtureScraperPlugin):
    """Aktin -- Czech/Slovak sports nutrition retailer."""

    RETAILER = RetailerSpec(
        slug="aktin",
        name="Aktin",
        base_url="https://aktin.sk",
        home_country="SK",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="2.99", free_over="49.00", min_days=1, max_days=2, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Aktin Whey Protein 1000 g",
                1000,
                "22.90",
                "/whey-1000g",
                protein_pct="74",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "Aktin Whey Protein 2000 g",
                2000,
                "42.90",
                "/whey-2000g",
                protein_pct="74",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Aktin Creatine Monohydrate 500 g",
                500,
                "13.90",
                "/creatine-500g",
                creatine_form=CreatineForm.STANDARD,
            ),
            OfferSpec(
                "Aktin Creatine Monohydrate 1000 g",
                1000,
                "22.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
