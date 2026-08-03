"""Tests for Money/Weight value objects."""

from __future__ import annotations

from decimal import Decimal

import pytest

from supplement_optimizer.domain.enums import Currency
from supplement_optimizer.domain.quantities import Money, Weight


def test_money_is_quantized_to_cents() -> None:
    assert Money(amount=Decimal("1.005"), currency=Currency.EUR).amount == Decimal("1.01")


def test_money_arithmetic() -> None:
    a = Money(amount=Decimal("10.00"), currency=Currency.EUR)
    b = Money(amount=Decimal("2.50"), currency=Currency.EUR)
    assert (a + b).amount == Decimal("12.50")
    assert (a - b).amount == Decimal("7.50")
    assert (a * 3).amount == Decimal("30.00")
    assert (3 * a).amount == Decimal("30.00")


def test_money_rejects_currency_mix() -> None:
    a = Money(amount=Decimal("1"), currency=Currency.EUR)
    b = Money(amount=Decimal("1"), currency=Currency.GBP)
    with pytest.raises(ValueError, match="Cannot combine"):
        _ = a + b


def test_money_is_immutable() -> None:
    a = Money(amount=Decimal("1"), currency=Currency.EUR)
    with pytest.raises(Exception):  # noqa: B017 - pydantic frozen error type varies
        a.amount = Decimal("2")  # type: ignore[misc]


def test_money_per_unit_and_zero_guard() -> None:
    a = Money(amount=Decimal("10"), currency=Currency.EUR)
    assert a.per(Decimal("2.5")) == Decimal("4")
    with pytest.raises(ValueError, match="zero quantity"):
        a.per(Decimal("0"))


def test_weight_conversions() -> None:
    w = Weight.from_kg(2.5)
    assert w.grams == Decimal("2500.000")
    assert w.kg == Decimal("2.5")
    assert (w + Weight.from_kg(0.5)).kg == Decimal("3.0")
