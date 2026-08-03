"""MyProtein scraper plugin (United Kingdom, GBP)."""

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
class MyProteinPlugin(FixtureScraperPlugin):
    """MyProtein -- large UK brand shipping across the EU; priced in GBP."""

    RETAILER = RetailerSpec(
        slug="myprotein",
        name="MyProtein",
        base_url="https://www.myprotein.com",
        home_country="GB",
        currency=Currency.GBP,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="5.99", free_over="55.00", min_days=3, max_days=7, methods=("courier",)
        ),
    )
    COUPONS = (CouponSpec("MP20", CouponType.PERCENT, value="0.20"),)
    CATALOG = {
        WHEY: (
            OfferSpec(
                "Impact Whey Protein 1 kg",
                1000,
                "24.99",
                "/impact-whey-1kg",
                protein_pct="80",
                serving_size_g="25",
                protein_per_serving_g="21",
            ),
            OfferSpec(
                "Impact Whey Protein 2.5 kg",
                2500,
                "54.99",
                "/impact-whey-2500g",
                protein_pct="80",
                serving_size_g="25",
                protein_per_serving_g="22",
                quantity_breaks=((2, "49.99"),),
            ),
            OfferSpec(
                "Impact Whey Protein 5 kg",
                5000,
                "99.99",
                "/impact-whey-5kg",
                protein_pct="82",
                serving_size_g="25",
                protein_per_serving_g="22",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Creatine Monohydrate 500 g",
                500,
                "11.99",
                "/creatine-500g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
            OfferSpec(
                "Creatine Monohydrate 1 kg",
                1000,
                "19.99",
                "/creatine-1kg",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }
