"""Minimum-cost package packing for a single retailer + single category.

Given the offers a retailer sells for one requirement (e.g. all its whey SKUs of
various pack sizes) and a target amount in grams, this computes the *cheapest*
combination of packages whose total content lands in ``[target_g, max_g]``.

This is a bounded multiple-choice knapsack solved exactly with a layered dynamic
program (one layer per offer, coverage measured in an integer gram grid). Pack
counts and target sizes are tiny, so an exact DP is fast, deterministic and
needs no external MILP solver. See ``docs/ARCHITECTURE_DECISIONS.md`` (ADR-0004).

Coverage is never clamped: a combination whose content exceeds ``max_g`` is
simply disallowed (it would break the requirement's overshoot tolerance). This
keeps predecessor reconstruction trivial and correct.
"""

from __future__ import annotations

import math
from decimal import Decimal

from pydantic import BaseModel

from supplement_optimizer.domain.enums import Currency
from supplement_optimizer.domain.models import Offer
from supplement_optimizer.domain.quantities import Money

_INF = Decimal("Infinity")


class PackingResult(BaseModel):
    """The cheapest packing for one category at one retailer."""

    lines: tuple[tuple[Offer, int], ...]
    product_cost: Money
    total_content_g: Decimal


def _grid_step(offers: list[Offer]) -> int:
    """Return the gcd of pack sizes (grams) -- the coarsest exact grid.

    Using the gcd keeps the DP exact while making the grid as coarse (and thus
    as fast) as possible. Falls back to 1 g if any pack size is fractional.
    """
    sizes: list[int] = []
    for offer in offers:
        if offer.pack_content_g != offer.pack_content_g.to_integral_value():
            return 1
        sizes.append(int(offer.pack_content_g))
    step = 0
    for size in sizes:
        step = math.gcd(step, size)
    return step or 1


def cheapest_packing(  # noqa: PLR0912 - one cohesive DP; splitting would obscure it
    offers: list[Offer],
    target_g: Decimal,
    max_g: Decimal,
    currency: Currency,
) -> PackingResult | None:
    """Return the cheapest packing with content in ``[target_g, max_g]``, or None.

    ``offers`` must already be filtered (available, ships to destination) and
    priced in ``currency``. Returns ``None`` when no combination fits the window.
    """
    if not offers:
        return None

    step = _grid_step(offers)
    target_cells = math.ceil(float(target_g) / step)
    cap = math.floor(float(max_g) / step)
    if cap < target_cells:
        return None

    n = len(offers)
    # layer[i][c] = min cost using offers[0..i-1] to reach exactly c cells.
    layers: list[list[Decimal]] = [[_INF] * (cap + 1) for _ in range(n + 1)]
    layers[0][0] = Decimal("0")
    # choice[i][c] = units of offers[i-1] taken to achieve layers[i][c].
    choice: list[list[int]] = [[0] * (cap + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        offer = offers[i - 1]
        pack_cells = max(1, round(float(offer.pack_content_g) / step))
        k_max = cap // pack_cells
        prev_layer = layers[i - 1]
        cur_layer = layers[i]
        cur_choice = choice[i]
        for prev_c in range(cap + 1):
            base = prev_layer[prev_c]
            if base == _INF:
                continue
            # k = 0..k_max units of this offer (multiple-choice knapsack).
            for k in range(k_max + 1):
                new_c = prev_c + pack_cells * k
                if new_c > cap:
                    break
                cost = base if k == 0 else base + offer.unit_price_for_quantity(k).amount * k
                if cost < cur_layer[new_c]:
                    cur_layer[new_c] = cost
                    cur_choice[new_c] = k

    # Cheapest coverage at or above the target in the final layer.
    final = layers[n]
    best_c, best_cost = -1, _INF
    for c in range(target_cells, cap + 1):
        if final[c] < best_cost:
            best_cost, best_c = final[c], c
    if best_c < 0 or best_cost == _INF:
        return None

    # Reconstruct chosen counts by walking layers back (predecessor is exact).
    counts: dict[int, int] = {}
    c = best_c
    for i in range(n, 0, -1):
        k = choice[i][c]
        if k > 0:
            counts[i - 1] = k
            pack_cells = max(1, round(float(offers[i - 1].pack_content_g) / step))
            c -= pack_cells * k

    lines = tuple((offers[idx], q) for idx, q in sorted(counts.items()))
    total_content = sum((offers[idx].pack_content_g * q for idx, q in counts.items()), Decimal("0"))
    return PackingResult(
        lines=lines,
        product_cost=Money(amount=best_cost, currency=currency),
        total_content_g=total_content,
    )
