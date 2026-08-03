"""Nutrend scraper plugin (Czechia, EUR)."""

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
class NutrendPlugin(FixtureScraperPlugin):
    """Nutrend -- established Czech manufacturer."""

    RETAILER = RetailerSpec(
        slug="nutrend",
        name="Nutrend",
        base_url="https://www.nutrend.cz",
        home_country="CZ",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="3.90", free_over="69.00", min_days=2, max_days=4, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Nutrend Whey Protein 1000 g",
                1000,
                "26.90",
                "/whey-1000g",
                protein_pct="73",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "Nutrend Whey Protein 2250 g",
                2250,
                "56.90",
                "/whey-2250g",
                protein_pct="73",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Nutrend Creatine Monohydrate 500 g",
                500,
                "15.90",
                "/creatine-500g",
                creatine_form=CreatineForm.STANDARD,
            ),
        ),
    }
