"""Sportnahrung Engel scraper plugin (Germany, EUR)."""

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
class SportnahrungEngelPlugin(FixtureScraperPlugin):
    """Sportnahrung Engel -- German retailer, EUR pricing."""

    RETAILER = RetailerSpec(
        slug="sportnahrung_engel",
        name="Sportnahrung Engel",
        base_url="https://www.sportnahrung-engel.de",
        home_country="DE",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="5.50", free_over="75.00", min_days=3, max_days=6, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Engel Whey Protein 1000 g",
                1000,
                "25.90",
                "/whey-1000g",
                protein_pct="74",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "Engel Whey Protein 2500 g",
                2500,
                "58.90",
                "/whey-2500g",
                protein_pct="74",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Engel Creatine Monohydrate 500 g",
                500,
                "15.50",
                "/creatine-500g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
