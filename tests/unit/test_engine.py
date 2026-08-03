"""Tests for the optimization engine."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from supplement_optimizer.domain.enums import CouponType, Currency, ShippingConfidence
from supplement_optimizer.domain.models import BasketRequest, Coupon, Requirement
from supplement_optimizer.optimizer.engine import OptimizationEngine
from supplement_optimizer.optimizer.rates import StaticRateProvider
from tests.conftest import eur, make_offer, make_retailer, make_shipping

WHEY = "whey_protein"
CREATINE = "creatine_monohydrate"


def _request() -> BasketRequest:
    return BasketRequest(
        requirements=(
            Requirement(category=WHEY, target_g=Decimal("5000")),
            Requirement(category=CREATINE, target_g=Decimal("2000")),
        ),
        destination_country="SK",
    )


def _engine(retailers, rules, coupons=None, **kw) -> OptimizationEngine:  # type: ignore[no-untyped-def]
    return OptimizationEngine(
        {r.slug: r for r in retailers},
        {(r.retailer_slug, r.destination_country): r for r in rules},
        coupons or {},
        StaticRateProvider({Currency.GBP: Decimal("0.85")}),
        **kw,
    )


def test_single_retailer_solution() -> None:
    offers = [make_offer("a", WHEY, 5000, 85), make_offer("a", CREATINE, 1000, 25)]
    engine = _engine([make_retailer("a")], [make_shipping("a", 5, free_over=100)])
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    assert sol.strategy == "single_retailer"
    # 85 + 2*25 = 135 -> above free-shipping threshold -> no shipping.
    assert sol.total.amount == Decimal("135.00")


def test_multi_retailer_split_is_chosen_when_cheaper() -> None:
    offers = [
        make_offer("a", WHEY, 5000, 85),
        make_offer("a", CREATINE, 1000, 25),
        make_offer("b", WHEY, 5000, 70),
        make_offer("b", CREATINE, 1000, 40),
    ]
    rules = [make_shipping("a", 5, free_over=100), make_shipping("b", 6, free_over=50)]
    engine = _engine([make_retailer("a"), make_retailer("b")], rules)
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    # whey from b (70, free) + creatine from a (50 + 5 shipping) = 125.
    assert sol.strategy == "multi_retailer"
    assert sol.total.amount == Decimal("125.00")
    assert sol.retailer_count == 2


def test_percentage_coupon_is_applied_when_beneficial() -> None:
    offers = [make_offer("a", WHEY, 5000, 100), make_offer("a", CREATINE, 1000, 25)]
    coupon = Coupon(
        retailer_slug="a", code="SAVE10", coupon_type=CouponType.PERCENT, value=Decimal("0.10")
    )
    engine = _engine([make_retailer("a")], [make_shipping("a", 5, free_over=500)], {"a": [coupon]})
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    sub = sol.sub_baskets[0]
    # subtotal 150, -10% = 135, + shipping 5 (below 500 threshold) = 140.
    assert sub.coupon_code == "SAVE10"
    assert sol.total.amount == Decimal("140.00")


def test_free_shipping_coupon_waives_shipping() -> None:
    offers = [make_offer("a", WHEY, 5000, 40), make_offer("a", CREATINE, 1000, 5)]
    coupon = Coupon(retailer_slug="a", code="FREESHIP", coupon_type=CouponType.FREE_SHIPPING)
    engine = _engine([make_retailer("a")], [make_shipping("a", 9, free_over=1000)], {"a": [coupon]})
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    # subtotal 50, shipping waived -> 50.
    assert sol.sub_baskets[0].coupon_code == "FREESHIP"
    assert sol.total.amount == Decimal("50.00")


def test_expired_coupon_is_ignored() -> None:
    offers = [make_offer("a", WHEY, 5000, 100), make_offer("a", CREATINE, 1000, 25)]
    coupon = Coupon(
        retailer_slug="a",
        code="OLD",
        coupon_type=CouponType.PERCENT,
        value=Decimal("0.50"),
        expires_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    engine = _engine([make_retailer("a")], [make_shipping("a", 0, free_over=0)], {"a": [coupon]})
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    assert sol.sub_baskets[0].coupon_code is None


def test_currency_conversion_affects_choice() -> None:
    # b priced in GBP; 60 GBP -> ~70.59 EUR, still cheaper than a's 85 EUR.
    offers = [
        make_offer("a", WHEY, 5000, 85),
        make_offer("a", CREATINE, 1000, 25),
        make_offer("b", WHEY, 5000, 60, currency=Currency.GBP),
        make_offer("b", CREATINE, 1000, 20, currency=Currency.GBP),
    ]
    rules = [make_shipping("a", 5, free_over=1000), make_shipping("b", 0, free_over=0)]
    engine = _engine([make_retailer("a"), make_retailer("b")], rules)
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    # Whole basket from b is cheapest once converted.
    assert {s.retailer_slug for s in sol.sub_baskets} == {"b"}


def test_missing_shipping_rule_is_marked_estimated() -> None:
    offers = [make_offer("a", WHEY, 5000, 85), make_offer("a", CREATINE, 1000, 25)]
    engine = _engine([make_retailer("a")], [], estimated_shipping=eur(7))
    sol = engine.optimize(_request(), offers)
    assert sol is not None
    assert sol.shipping_confidence is ShippingConfidence.ESTIMATED
    assert sol.total.amount == Decimal("142.00")  # 135 goods + 7 estimated shipping


def test_infeasible_requirement_returns_none() -> None:
    offers = [make_offer("a", WHEY, 5000, 85)]  # no creatine anywhere
    engine = _engine([make_retailer("a")], [make_shipping("a", 5)])
    assert engine.optimize(_request(), offers) is None


def test_offer_not_shipping_to_destination_is_excluded() -> None:
    offers = [make_offer("a", WHEY, 5000, 85), make_offer("a", CREATINE, 1000, 25)]
    retailer = make_retailer("a", ships_to={"DE"})  # not SK
    engine = _engine([retailer], [make_shipping("a", 5)])
    assert engine.optimize(_request(), offers) is None
