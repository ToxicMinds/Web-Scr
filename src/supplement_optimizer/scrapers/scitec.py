"""Scitec Nutrition scraper plugin (Hungary, EUR)."""

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
class ScitecPlugin(FixtureScraperPlugin):
    """Scitec Nutrition -- Hungarian brand, EUR pricing."""

    RETAILER = RetailerSpec(
        slug="scitec",
        name="Scitec Nutrition",
        base_url="https://scitecnutrition.com",
        home_country="HU",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="4.20", free_over="65.00", min_days=2, max_days=5, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "100% Whey Protein Professional 920 g",
                920,
                "24.90",
                "/whey-pro-920g",
                protein_pct="72",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "100% Whey Protein Professional 2350 g",
                2350,
                "54.90",
                "/whey-pro-2350g",
                protein_pct="72",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Creatine 100% Pure 1000 g",
                1000,
                "26.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.STANDARD,
            ),
        ),
    }
