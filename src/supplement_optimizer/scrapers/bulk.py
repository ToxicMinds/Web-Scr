"""Bulk (formerly Bulk Powders) scraper plugin (United Kingdom, GBP)."""

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
class BulkPlugin(FixtureScraperPlugin):
    """Bulk -- UK retailer known for large pack sizes; priced in GBP."""

    RETAILER = RetailerSpec(
        slug="bulk",
        name="Bulk",
        base_url="https://www.bulk.com",
        home_country="GB",
        currency=Currency.GBP,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="6.99", free_over="99.00", min_days=3, max_days=8, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Pure Whey Protein 1 kg",
                1000,
                "22.99",
                "/pure-whey-1kg",
                protein_pct="78",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "Pure Whey Protein 2.5 kg",
                2500,
                "49.99",
                "/pure-whey-2500g",
                protein_pct="78",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "Pure Whey Protein 5 kg",
                5000,
                "89.99",
                "/pure-whey-5kg",
                protein_pct="78",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Creatine Monohydrate 1 kg",
                1000,
                "17.99",
                "/creatine-1kg",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
