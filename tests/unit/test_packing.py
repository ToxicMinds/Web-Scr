"""Tests for the exact packing DP (:func:`cheapest_packing`)."""

from __future__ import annotations

from decimal import Decimal

from supplement_optimizer.domain.enums import Currency
from supplement_optimizer.domain.models import QuantityBreak
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.optimizer.packing import cheapest_packing
from tests.conftest import make_offer


def _content(result: object) -> Decimal:
    return result.total_content_g  # type: ignore[union-attr]


def test_prefers_single_large_pack_over_many_small() -> None:
    offers = [
        make_offer("a", "whey", 1000, 20),
        make_offer("a", "whey", 2500, 45),
        make_offer("a", "whey", 5000, 85),
    ]
    result = cheapest_packing(offers, Decimal("5000"), Decimal("6250"), Currency.EUR)
    assert result is not None
    assert result.product_cost.amount == Decimal("85.00")
    assert result.total_content_g == Decimal("5000")
    assert result.lines == ((offers[2], 1),)


def test_combines_packs_when_cheaper_per_gram() -> None:
    # 500g @ 8 (16/kg) beats 1000g @ 20 (20/kg): four 500g packs reach 2kg @ 32.
    offers = [make_offer("a", "cre", 500, 8), make_offer("a", "cre", 1000, 20)]
    result = cheapest_packing(offers, Decimal("2000"), Decimal("2500"), Currency.EUR)
    assert result is not None
    assert result.product_cost.amount == Decimal("32.00")
    assert {o.pack_content_g: q for o, q in result.lines} == {Decimal("500"): 4}


def test_returns_none_when_infeasible_within_tolerance() -> None:
    # Only a 5kg pack available but max is 3kg -> cannot fit the window.
    offers = [make_offer("a", "whey", 5000, 85)]
    assert cheapest_packing(offers, Decimal("2000"), Decimal("3000"), Currency.EUR) is None


def test_honours_quantity_breaks() -> None:
    offer = make_offer(
        "a",
        "whey",
        1000,
        20,
        quantity_breaks=(
            QuantityBreak(
                min_quantity=5, unit_price=Money(amount=Decimal("15"), currency=Currency.EUR)
            ),
        ),
    )
    result = cheapest_packing([offer], Decimal("5000"), Decimal("6000"), Currency.EUR)
    assert result is not None
    # 5 units at the bulk price of 15 = 75, not 100.
    assert result.product_cost.amount == Decimal("75.00")
    assert result.lines == ((offer, 5),)


def test_empty_offers_returns_none() -> None:
    assert cheapest_packing([], Decimal("1000"), Decimal("2000"), Currency.EUR) is None
