"""Amazon Germany scraper plugin (Germany, EUR)."""

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
class AmazonDePlugin(FixtureScraperPlugin):
    """Amazon.de -- marketplace aggregating multiple third-party brands (EUR)."""

    RETAILER = RetailerSpec(
        slug="amazon_de",
        name="Amazon Germany",
        base_url="https://www.amazon.de",
        home_country="DE",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="0.00", free_over="0.00", min_days=2, max_days=5, methods=("prime",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "ESN Designer Whey 1000 g",
                1000,
                "26.99",
                "/esn-whey-1000g",
                protein_pct="76",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "ESN Designer Whey 2500 g",
                2500,
                "59.99",
                "/esn-whey-2500g",
                protein_pct="76",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "ESN Creatine Monohydrate 500 g",
                500,
                "14.49",
                "/esn-creatine-500g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
            OfferSpec(
                "ESN Creatine Monohydrate 1000 g",
                1000,
                "24.99",
                "/esn-creatine-1000g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
