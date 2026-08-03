"""Bulk (formerly Bulk Powders) scraper plugin (United Kingdom, GBP).

Bulk runs standard Magento 2; product data comes from its ``/graphql`` API when
``scraper_live`` is enabled (ADR-0006). Otherwise the offline seed catalog below
is used for deterministic tests/CI.
"""

from __future__ import annotations

from supplement_optimizer.domain.enums import CreatineForm, Currency, ProductCategory
from supplement_optimizer.plugins.registry import register
from supplement_optimizer.scrapers._fixture import (
    OfferSpec,
    RetailerSpec,
    ShippingSpec,
)
from supplement_optimizer.scrapers.constants import EU_SHIPS
from supplement_optimizer.scrapers.magento_graphql import MagentoGraphQLScraper

WHEY = ProductCategory.WHEY_PROTEIN.value
CREATINE = ProductCategory.CREATINE_MONOHYDRATE.value


@register
class BulkPlugin(MagentoGraphQLScraper):
    """Bulk -- UK retailer known for large pack sizes; priced in GBP."""

    RETAILER = RetailerSpec(
        slug="bulk",
        name="Bulk",
        base_url="https://www.bulk.com/uk",
        home_country="GB",
        currency=Currency.GBP,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="6.99", free_over="99.00", min_days=3, max_days=8, methods=("courier",)
        ),
    )
    GRAPHQL_URL = "https://www.bulk.com/graphql"
    VARIANTS_FIELD = "variants"
    BRAND = "Bulk"
    SEARCH = {
        WHEY: ("pure whey protein", "whey protein"),
        CREATINE: ("creatine monohydrate",),
    }

    # Deterministic offline seed catalog (used when scraper_live is False).
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
