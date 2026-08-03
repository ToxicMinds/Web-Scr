"""Amazon Poland scraper plugin (Poland, PLN)."""

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
class AmazonPlPlugin(FixtureScraperPlugin):
    """Amazon.pl -- Polish marketplace, priced in PLN (exercises FX handling)."""

    RETAILER = RetailerSpec(
        slug="amazon_pl",
        name="Amazon Poland",
        base_url="https://www.amazon.pl",
        home_country="PL",
        currency=Currency.PLN,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="19.90", free_over="200.00", min_days=2, max_days=6, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Olimp Whey Protein Complex 1800 g",
                1800,
                "129.00",
                "/olimp-whey-1800g",
                protein_pct="72",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "Olimp Whey Protein Complex 2270 g",
                2270,
                "159.00",
                "/olimp-whey-2270g",
                protein_pct="72",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Olimp Creatine Monohydrate Powder 550 g",
                550,
                "39.00",
                "/olimp-creatine-550g",
                creatine_form=CreatineForm.STANDARD,
            ),
        ),
    }
