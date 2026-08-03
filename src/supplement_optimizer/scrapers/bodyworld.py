"""BodyWorld scraper plugin (Slovakia, EUR)."""

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
class BodyWorldPlugin(FixtureScraperPlugin):
    """BodyWorld -- Slovak retailer, local EUR pricing and fast delivery."""

    RETAILER = RetailerSpec(
        slug="bodyworld",
        name="BodyWorld",
        base_url="https://www.bodyworld.sk",
        home_country="SK",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="3.20", free_over="50.00", min_days=1, max_days=2, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "BodyWorld Whey 1000 g",
                1000,
                "23.50",
                "/whey-1000g",
                protein_pct="75",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "BodyWorld Whey 4000 g",
                4000,
                "84.90",
                "/whey-4000g",
                protein_pct="75",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "BodyWorld Creatine Monohydrate 500 g",
                500,
                "13.50",
                "/creatine-500g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
            OfferSpec(
                "BodyWorld Creatine Monohydrate 1000 g",
                1000,
                "23.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
