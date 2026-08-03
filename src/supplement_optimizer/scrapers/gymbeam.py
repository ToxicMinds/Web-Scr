"""GymBeam scraper plugin (Slovakia, EUR)."""

from __future__ import annotations

from supplement_optimizer.domain.enums import CouponType, CreatineForm, Currency, ProductCategory
from supplement_optimizer.plugins.registry import register
from supplement_optimizer.scrapers._fixture import (
    CouponSpec,
    FixtureScraperPlugin,
    OfferSpec,
    RetailerSpec,
    ShippingSpec,
)
from supplement_optimizer.scrapers.constants import EU_SHIPS

WHEY = ProductCategory.WHEY_PROTEIN.value
CREATINE = ProductCategory.CREATINE_MONOHYDRATE.value


@register
class GymBeamPlugin(FixtureScraperPlugin):
    """GymBeam -- large Slovak retailer, ships across Central Europe."""

    RETAILER = RetailerSpec(
        slug="gymbeam",
        name="GymBeam",
        base_url="https://gymbeam.sk",
        home_country="SK",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="3.49", free_over="59.90", min_days=1, max_days=3, methods=("courier",)
        ),
    )
    COUPONS = (CouponSpec("GYMBEAM5", CouponType.PERCENT, value="0.05", min_subtotal="50"),)
    CATALOG = {
        WHEY: (
            OfferSpec(
                "GymBeam True Whey 1000 g",
                1000,
                "24.90",
                "/true-whey-1000g",
                protein_pct="72",
                serving_size_g="30",
                protein_per_serving_g="22",
                flavours=("chocolate", "vanilla"),
            ),
            OfferSpec(
                "GymBeam True Whey 2500 g",
                2500,
                "54.90",
                "/true-whey-2500g",
                protein_pct="72",
                serving_size_g="30",
                protein_per_serving_g="22",
            ),
            OfferSpec(
                "GymBeam 100% Whey 5000 g",
                5000,
                "99.90",
                "/whey-5000g",
                protein_pct="70",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "GymBeam Creatine Monohydrate 500 g",
                500,
                "14.90",
                "/creatine-500g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
            OfferSpec(
                "GymBeam Creatine Monohydrate 1000 g",
                1000,
                "24.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
