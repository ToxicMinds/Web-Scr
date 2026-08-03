"""The Protein Works scraper plugin (United Kingdom, GBP).

Standard Magento 2 GraphQL (ADR-0006). Live when scraper_live is enabled; the
offline seed catalog below is used otherwise.
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
class ProteinWorksPlugin(MagentoGraphQLScraper):
    """The Protein Works -- UK retailer, GBP pricing."""

    RETAILER = RetailerSpec(
        slug="protein_works",
        name="The Protein Works",
        base_url="https://www.theproteinworks.com",
        home_country="GB",
        currency=Currency.GBP,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="7.99", free_over="120.00", min_days=4, max_days=8, methods=("courier",)
        ),
    )

    GRAPHQL_URL = "https://www.theproteinworks.com/graphql"
    VARIANTS_FIELD = "variants"
    BRAND = "The Protein Works"
    SEARCH = {
        WHEY: ("whey protein", "whey isolate"),
        CREATINE: ("creatine monohydrate",),
    }

    # Deterministic offline seed catalog (used when scraper_live is False).
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Whey Protein 80 1 kg",
                1000,
                "21.99",
                "/whey-80-1kg",
                protein_pct="80",
                serving_size_g="25",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "Whey Protein 80 4 kg",
                4000,
                "74.99",
                "/whey-80-4kg",
                protein_pct="80",
                serving_size_g="25",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Creatine Monohydrate 1 kg",
                1000,
                "18.99",
                "/creatine-1kg",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
