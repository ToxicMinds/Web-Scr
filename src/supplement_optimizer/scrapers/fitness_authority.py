"""Fitness Authority scraper plugin (Poland, EUR)."""

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
class FitnessAuthorityPlugin(FixtureScraperPlugin):
    """Fitness Authority (FA) -- Polish brand, EU store priced in EUR."""

    RETAILER = RetailerSpec(
        slug="fitness_authority",
        name="Fitness Authority",
        base_url="https://www.faonline.eu",
        home_country="PL",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="4.80", free_over="70.00", min_days=3, max_days=6, methods=("courier",)
        ),
    )
    CATALOG = {
        WHEY: (
            OfferSpec(
                "FA Whey Protein 900 g",
                900,
                "22.90",
                "/whey-900g",
                protein_pct="73",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "FA Whey Protein 2000 g",
                2000,
                "45.90",
                "/whey-2000g",
                protein_pct="73",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "FA Creatine Monohydrate 1000 g",
                1000,
                "21.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.STANDARD,
            ),
        ),
    }
