"""Prozis scraper plugin (Portugal, EUR)."""

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
class ProzisPlugin(FixtureScraperPlugin):
    """Prozis -- pan-European retailer, EUR pricing."""

    RETAILER = RetailerSpec(
        slug="prozis",
        name="Prozis",
        base_url="https://www.prozis.com",
        home_country="PT",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="4.90", free_over="79.00", min_days=3, max_days=6, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "100% Real Whey Protein 1000 g",
                1000,
                "25.99",
                "/real-whey-1000g",
                protein_pct="76",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "100% Real Whey Protein 2000 g",
                2000,
                "46.99",
                "/real-whey-2000g",
                protein_pct="76",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Creatine Monohydrate 300 g",
                300,
                "9.99",
                "/creatine-300g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
            OfferSpec(
                "Creatine Monohydrate 1000 g",
                1000,
                "23.99",
                "/creatine-1000g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
