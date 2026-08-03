"""BioTechUSA scraper plugin (Hungary, EUR)."""

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
class BioTechUsaPlugin(FixtureScraperPlugin):
    """BioTechUSA -- major Hungarian brand with EU-wide distribution."""

    RETAILER = RetailerSpec(
        slug="biotechusa",
        name="BioTechUSA",
        base_url="https://shop.biotechusa.com",
        home_country="HU",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="4.50", free_over="60.00", min_days=2, max_days=5, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "100% Pure Whey 1000 g",
                1000,
                "27.90",
                "/pure-whey-1000g",
                protein_pct="70",
                serving_size_g="28",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "100% Pure Whey 2270 g",
                2270,
                "57.90",
                "/pure-whey-2270g",
                protein_pct="70",
                serving_size_g="28",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "100% Creatine Monohydrate 500 g",
                500,
                "16.90",
                "/creatine-500g",
                creatine_form=CreatineForm.STANDARD,
            ),
            OfferSpec(
                "100% Creatine Monohydrate 1000 g",
                1000,
                "28.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.STANDARD,
            ),
        ),
    }
