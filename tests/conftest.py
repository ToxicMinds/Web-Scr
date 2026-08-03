"""Shared pytest fixtures and builders.

Small factory helpers keep tests terse and intent-revealing without hiding the
values that matter to each assertion.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from supplement_optimizer.domain.enums import Availability, Currency, ShippingConfidence
from supplement_optimizer.domain.models import Offer, Retailer, ShippingRule
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.optimizer.rates import StaticRateProvider


def eur(value: str | int) -> Money:
    """Convenience constructor for EUR money."""
    return Money(amount=Decimal(str(value)), currency=Currency.EUR)


def make_offer(
    slug: str,
    category: str,
    grams: int,
    price: str | int,
    *,
    currency: Currency = Currency.EUR,
    availability: Availability = Availability.IN_STOCK,
    **kwargs: object,
) -> Offer:
    """Build an :class:`Offer` with sensible defaults for tests."""
    return Offer(
        retailer_slug=slug,
        category=category,
        title=f"{grams}g pack",
        url=f"https://example.test/{slug}/{category}/{grams}",
        pack_content_g=Decimal(grams),
        price=Money(amount=Decimal(str(price)), currency=currency),
        availability=availability,
        **kwargs,  # type: ignore[arg-type]
    )


def make_retailer(slug: str, *, ships_to: set[str] | None = None) -> Retailer:
    """Build an active :class:`Retailer` shipping to ``ships_to`` (default SK)."""
    return Retailer(
        slug=slug,
        name=slug.title(),
        base_url=f"https://{slug}.test",
        home_country="SK",
        currency=Currency.EUR,
        ships_to=frozenset(ships_to or {"SK"}),
    )


def make_shipping(
    slug: str, cost: str | int, *, free_over: str | int | None = None, dest: str = "SK"
) -> ShippingRule:
    """Build a DETERMINED shipping rule for ``slug`` -> ``dest``."""
    return ShippingRule(
        retailer_slug=slug,
        destination_country=dest,
        cost=eur(cost),
        free_threshold=eur(free_over) if free_over is not None else None,
        confidence=ShippingConfidence.DETERMINED,
    )


@pytest.fixture
def rates() -> StaticRateProvider:
    """A static EUR-pivot rate provider covering the common currencies."""
    return StaticRateProvider(
        {
            Currency.GBP: Decimal("0.85"),
            Currency.PLN: Decimal("4.30"),
            Currency.CZK: Decimal("25.0"),
            Currency.USD: Decimal("1.08"),
        }
    )
