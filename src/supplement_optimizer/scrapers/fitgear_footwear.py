"""FitGear Footwear scraper plugin (Germany, EUR) -- Tier 3 demonstration.

Gym shoes are a *different shape* of product: discrete, sized items rather than a
divisible weight. This plugin proves the platform absorbs that with **no engine
rewrite**: each SKU sets ``pack_content_g=1`` (one pair = one unit) and carries
``size``/``colour``/``gender`` in the generic :attr:`OfferSpec.attributes` bag.
A :class:`Requirement` with ``unit='unit'`` and matching ``attributes`` then
selects the cheapest qualifying pair via the same packing + assignment logic.
"""

from __future__ import annotations

from supplement_optimizer.domain.enums import Currency, ProductCategory
from supplement_optimizer.plugins.registry import register
from supplement_optimizer.scrapers._fixture import (
    FixtureScraperPlugin,
    OfferSpec,
    RetailerSpec,
    ShippingSpec,
)
from supplement_optimizer.scrapers.constants import EU_SHIPS

SHOES = ProductCategory.GYM_SHOES.value


def _shoe(
    name: str, price: str, path: str, *, size: str, colour: str, gender: str = "unisex"
) -> OfferSpec:
    """Build a one-pair (content = 1 unit) shoe offer with its attributes."""
    return OfferSpec(
        title=name,
        pack_content_g=1,
        price=price,
        path=path,
        attributes={"size": size, "colour": colour, "gender": gender},
    )


@register
class FitGearFootwearPlugin(FixtureScraperPlugin):
    """FitGear -- German gym-footwear retailer, prices in EUR."""

    RETAILER = RetailerSpec(
        slug="fitgear_footwear",
        name="FitGear Footwear",
        base_url="https://fitgear.de",
        home_country="DE",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="5.90", free_over="80", min_days=2, max_days=5, methods=("courier",)
        ),
    )
    CATALOG = {
        SHOES: (
            _shoe(
                "FitGear Metcon Trainer", "119.00", "/metcon-43-black", size="43", colour="black"
            ),
            _shoe(
                "FitGear Metcon Trainer", "109.00", "/metcon-43-white", size="43", colour="white"
            ),
            _shoe(
                "FitGear Metcon Trainer", "119.00", "/metcon-44-black", size="44", colour="black"
            ),
            _shoe("FitGear Power Lifter", "139.00", "/power-43-black", size="43", colour="black"),
            _shoe("FitGear Studio Sneaker", "79.00", "/studio-42-black", size="42", colour="black"),
        ),
    }
