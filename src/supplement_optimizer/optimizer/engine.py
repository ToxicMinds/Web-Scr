"""The category-agnostic optimization engine.

The engine answers: *what is the cheapest way to buy every requirement in a
:class:`BasketRequest`, delivered to a country, across all retailers?* It knows
nothing about protein or creatine -- only requirements (a category key + a gram
target) and offers.

Model & guarantees
------------------
* Per retailer + category, the cheapest package combination is found **exactly**
  by :func:`cheapest_packing` (bulk pricing = multiple pack sizes and/or
  quantity breaks are both honoured).
* Retailer-level costs add shipping (with free-shipping thresholds) and the best
  applicable coupon.
* Across retailers, every assignment of *requirement -> retailer* is enumerated
  and the cheapest total wins. This finds the global optimum under one explicit
  modelling assumption: each requirement is sourced from a single retailer (no
  splitting one requirement across stores). This captures single-retailer,
  multi-retailer, shipping, free-shipping, coupons, bulk discounts and package
  combinations. The assumption and its rationale are recorded in ADR-0004.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from supplement_optimizer.config.logging import get_logger
from supplement_optimizer.domain.enums import CouponType, Currency, ShippingConfidence
from supplement_optimizer.domain.models import (
    BasketRequest,
    Coupon,
    Offer,
    Retailer,
    ShippingRule,
)
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.optimizer.models import BasketLine, RetailerSubBasket, Solution
from supplement_optimizer.optimizer.packing import PackingResult, cheapest_packing
from supplement_optimizer.optimizer.rates import RateProvider

_logger = get_logger(__name__)

_CONFIDENCE_ORDER = {
    ShippingConfidence.DETERMINED: 0,
    ShippingConfidence.ESTIMATED: 1,
    ShippingConfidence.UNKNOWN: 2,
}


def _matches_attributes(offer: Offer, constraints: dict[str, str]) -> bool:
    """Whether ``offer`` satisfies every attribute constraint (case-insensitive)."""
    for key, value in constraints.items():
        actual = offer.attributes.get(key)
        if actual is None or actual.strip().lower() != value.strip().lower():
            return False
    return True


@dataclass(frozen=True)
class _CouponOutcome:
    """The effect of applying (or not) a coupon at one retailer."""

    code: str | None
    goods_discount: Money
    waive_shipping: bool


class OptimizationEngine:
    """Finds the cheapest basket for a :class:`BasketRequest`.

    All collaborators are injected (Dependency Injection): retailers, shipping
    rules, coupons and the currency :class:`RateProvider`. The engine performs no
    I/O -- it is pure and therefore trivially testable.
    """

    def __init__(
        self,
        retailers: dict[str, Retailer],
        shipping_rules: dict[tuple[str, str], ShippingRule],
        coupons: dict[str, list[Coupon]],
        rate_provider: RateProvider,
        *,
        estimated_shipping: Money | None = None,
        now: datetime | None = None,
    ) -> None:
        self._retailers = retailers
        self._shipping_rules = shipping_rules
        self._coupons = coupons
        self._rates = rate_provider
        self._estimated_shipping = estimated_shipping
        self._now = now or datetime.now(UTC)

    # -- public API -------------------------------------------------------

    def optimize(self, request: BasketRequest, offers: list[Offer]) -> Solution | None:
        """Return the cheapest feasible :class:`Solution`, or ``None``."""
        base = request.base_currency
        dest = request.destination_country
        priced = self._prepare_offers(offers, request, base)

        # Cache the cheapest packing per (retailer, category).
        packings: dict[tuple[str, str], PackingResult] = {}
        candidates: dict[str, list[str]] = {}
        for req in request.requirements:
            slugs: list[str] = []
            for slug in sorted(self._retailers):
                bucket = priced.get((slug, req.category))
                if not bucket:
                    continue
                # Discrete-item requirements (Tier 3) constrain on attributes
                # such as size/colour; divisible goods have no constraints.
                if req.attributes:
                    bucket = [o for o in bucket if _matches_attributes(o, req.attributes)]
                    if not bucket:
                        continue
                result = cheapest_packing(bucket, req.target_g, req.max_g, base)
                if result is not None:
                    packings[slug, req.category] = result
                    slugs.append(slug)
            if not slugs:
                _logger.warning("requirement_infeasible", category=req.category)
                return None
            candidates[req.category] = slugs

        best: Solution | None = None
        categories = [r.category for r in request.requirements]
        for combo in itertools.product(*(candidates[c] for c in categories)):
            assignment = dict(zip(categories, combo, strict=True))
            solution = self._build_solution(request, assignment, packings, base, dest)
            if best is None or solution.total < best.total:
                best = solution
        return best

    # -- internals --------------------------------------------------------

    def _prepare_offers(
        self, offers: list[Offer], request: BasketRequest, base: Currency
    ) -> dict[tuple[str, str], list[Offer]]:
        """Filter to deliverable, available offers and price them in ``base``."""
        wanted = {r.category for r in request.requirements}
        dest = request.destination_country
        buckets: dict[tuple[str, str], list[Offer]] = {}
        for offer in offers:
            if offer.category not in wanted or not offer.is_available():
                continue
            retailer = self._retailers.get(offer.retailer_slug)
            if retailer is None or not retailer.active:
                continue
            ships = offer.ships_to if offer.ships_to is not None else retailer.ships_to
            if dest not in ships:
                continue
            buckets.setdefault((offer.retailer_slug, offer.category), []).append(
                self._to_base(offer, base)
            )
        return buckets

    def _to_base(self, offer: Offer, base: Currency) -> Offer:
        """Return a copy of ``offer`` with all prices converted to ``base``."""
        if offer.price.currency == base and all(
            qb.unit_price.currency == base for qb in offer.quantity_breaks
        ):
            return offer
        breaks = tuple(
            qb.model_copy(update={"unit_price": self._rates.convert(qb.unit_price, base)})
            for qb in offer.quantity_breaks
        )
        return offer.model_copy(
            update={"price": self._rates.convert(offer.price, base), "quantity_breaks": breaks}
        )

    def _build_solution(
        self,
        request: BasketRequest,
        assignment: dict[str, str],
        packings: dict[tuple[str, str], PackingResult],
        base: Currency,
        dest: str,
    ) -> Solution:
        """Cost a single requirement->retailer assignment into a Solution."""
        by_retailer: dict[str, list[str]] = {}
        for category, slug in assignment.items():
            by_retailer.setdefault(slug, []).append(category)

        sub_baskets: list[RetailerSubBasket] = []
        fulfilled: dict[str, Decimal] = {}
        total = Money.zero(base)
        worst_conf = ShippingConfidence.DETERMINED

        for slug, categories in sorted(by_retailer.items()):
            lines: list[BasketLine] = []
            product_subtotal = Money.zero(base)
            for category in categories:
                packing = packings[slug, category]
                fulfilled[category] = packing.total_content_g
                product_subtotal = product_subtotal + packing.product_cost
                for offer, qty in packing.lines:
                    unit = offer.unit_price_for_quantity(qty)
                    lines.append(
                        BasketLine(
                            offer=offer,
                            quantity=qty,
                            unit_price=unit,
                            line_total=unit * qty,
                            content_g=offer.pack_content_g * qty,
                        )
                    )

            ship_cost, ship_conf = self._shipping(slug, dest, product_subtotal, base)
            coupon = self._best_coupon(slug, product_subtotal, ship_cost, base)
            effective_shipping = Money.zero(base) if coupon.waive_shipping else ship_cost
            retailer_total = product_subtotal - coupon.goods_discount + effective_shipping

            sub_baskets.append(
                RetailerSubBasket(
                    retailer_slug=slug,
                    lines=tuple(lines),
                    product_subtotal=product_subtotal,
                    coupon_code=coupon.code,
                    coupon_discount=coupon.goods_discount,
                    shipping_cost=effective_shipping,
                    shipping_confidence=ship_conf,
                    total=retailer_total,
                )
            )
            total = total + retailer_total
            if _CONFIDENCE_ORDER[ship_conf] > _CONFIDENCE_ORDER[worst_conf]:
                worst_conf = ship_conf

        strategy = "single_retailer" if len(by_retailer) == 1 else "multi_retailer"
        return Solution(
            strategy=strategy,
            currency=base,
            sub_baskets=tuple(sub_baskets),
            total=total,
            fulfilled_g=fulfilled,
            shipping_confidence=worst_conf,
        )

    def _shipping(
        self, slug: str, dest: str, product_subtotal: Money, base: Currency
    ) -> tuple[Money, ShippingConfidence]:
        """Resolve shipping cost + confidence for one retailer.

        Free-shipping thresholds are evaluated on the pre-coupon product
        subtotal (the convention used by the vast majority of stores).
        """
        rule = self._shipping_rules.get((slug, dest))
        if rule is None:
            fallback = self._estimated_shipping or Money.zero(base)
            return self._rates.convert(fallback, base), ShippingConfidence.ESTIMATED
        if rule.free_threshold is not None:
            threshold = self._rates.convert(rule.free_threshold, base)
            if product_subtotal.amount >= threshold.amount:
                return Money.zero(base), rule.confidence
        return self._rates.convert(rule.cost, base), rule.confidence

    def _best_coupon(
        self, slug: str, product_subtotal: Money, shipping: Money, base: Currency
    ) -> _CouponOutcome:
        """Pick the coupon that minimises this retailer's total (or none)."""
        best = _CouponOutcome(code=None, goods_discount=Money.zero(base), waive_shipping=False)
        best_total = product_subtotal + shipping
        for coupon in self._coupons.get(slug, []):
            if not coupon.is_valid_at(self._now):
                continue
            if coupon.min_subtotal is not None:
                min_sub = self._rates.convert(coupon.min_subtotal, base)
                if product_subtotal.amount < min_sub.amount:
                    continue
            outcome = self._evaluate_coupon(coupon, product_subtotal, base)
            eff_ship = Money.zero(base) if outcome.waive_shipping else shipping
            candidate_total = product_subtotal - outcome.goods_discount + eff_ship
            if candidate_total < best_total:
                best_total = candidate_total
                best = outcome
        return best

    def _evaluate_coupon(
        self, coupon: Coupon, product_subtotal: Money, base: Currency
    ) -> _CouponOutcome:
        """Translate a coupon into a concrete discount/shipping effect."""
        if coupon.coupon_type is CouponType.FREE_SHIPPING:
            return _CouponOutcome(
                code=coupon.code, goods_discount=Money.zero(base), waive_shipping=True
            )
        if coupon.coupon_type is CouponType.PERCENT:
            discount = Money(amount=product_subtotal.amount * coupon.value, currency=base)
            return _CouponOutcome(code=coupon.code, goods_discount=discount, waive_shipping=False)
        # FIXED amount, converted into the base currency.
        raw = Money(amount=coupon.value, currency=coupon.currency or base)
        converted = self._rates.convert(raw, base)
        capped = min(converted.amount, product_subtotal.amount)
        return _CouponOutcome(
            code=coupon.code,
            goods_discount=Money(amount=capped, currency=base),
            waive_shipping=False,
        )
