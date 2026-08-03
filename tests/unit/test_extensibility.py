"""Extensibility proofs: adding a retailer (Tier 1), a divisible ingredient
(Tier 2) and a discrete sized item with size/colour (Tier 3) — all without
touching the optimization engine's core algorithm.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from supplement_optimizer.domain.enums import Currency, ProductCategory
from supplement_optimizer.domain.models import BasketRequest, Offer, Requirement
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.optimizer.rates import default_rate_provider
from supplement_optimizer.plugins.filters import filter_for
from supplement_optimizer.plugins.registry import PluginRegistry
from supplement_optimizer.service import OptimizationService

OMEGA3 = ProductCategory.OMEGA_3.value
SHOES = ProductCategory.GYM_SHOES.value


def _run(request: BasketRequest):
    service = OptimizationService(rate_provider=default_rate_provider())
    return asyncio.run(service.run(request))


# --- Tier 1: a new retailer is just one registered plugin --------------------


def test_tier1_new_retailer_is_discovered() -> None:
    registry = PluginRegistry()
    slugs = set(registry.slugs())
    assert "prom_in" in slugs
    plugin = registry.create("prom_in")
    retailer = plugin.retailer()
    assert retailer.currency is Currency.CZK
    assert retailer.ships_to_country("SK")


def test_tier1_new_retailer_offers_participate() -> None:
    request = BasketRequest(
        requirements=(
            Requirement(category=ProductCategory.WHEY_PROTEIN.value, target_g=Decimal("2000")),
        ),
        destination_country="SK",
    )
    result = _run(request)
    assert result.solution is not None
    # Prom-IN's CZK-priced whey is available to the optimizer (priced in EUR).
    assert any(o.retailer_slug == "prom_in" for o in result.market.offers)


# --- Tier 2: a new divisible ingredient needs a filter + category + offers ----


def test_tier2_new_ingredient_optimizes() -> None:
    request = BasketRequest(
        requirements=(Requirement(category=OMEGA3, target_g=Decimal("500")),),
        destination_country="SK",
    )
    result = _run(request)
    assert result.solution is not None
    # Every purchased line is genuinely an omega-3 offer that passed the filter.
    lines = [line for sub in result.solution.sub_baskets for line in sub.lines]
    assert lines
    assert all(line.offer.category == OMEGA3 for line in lines)
    assert result.solution.fulfilled_g[OMEGA3] >= Decimal("500")


def test_tier2_filter_rejects_non_fish_oil() -> None:
    flt = filter_for(OMEGA3)
    assert flt is not None
    good = Offer(
        retailer_slug="x",
        category=OMEGA3,
        title="Omega-3 Fish Oil 250 g",
        url="u",
        pack_content_g=Decimal("250"),
        price=Money(amount=Decimal("9"), currency=Currency.EUR),
    )
    plant = good.model_copy(update={"title": "Vegan Algae Omega-3 250 g"})
    assert flt.accepts(good) is True
    assert flt.accepts(plant) is False


# --- Tier 3: a discrete sized item selected by size + colour ------------------


def _shoe_request(size: str, colour: str) -> BasketRequest:
    return BasketRequest(
        requirements=(
            Requirement(
                category=SHOES,
                target_g=Decimal("1"),
                tolerance=Decimal("0"),
                unit="unit",
                attributes={"size": size, "colour": colour},
            ),
        ),
        destination_country="SK",
    )


def test_tier3_picks_cheapest_matching_size_and_colour() -> None:
    result = _run(_shoe_request(size="43", colour="black"))
    assert result.solution is not None
    lines = [line for sub in result.solution.sub_baskets for line in sub.lines]
    assert len(lines) == 1
    chosen = lines[0].offer
    # Cheapest black size-43 pair is the 119.00 Metcon, not the 139.00 Power Lifter.
    assert chosen.attributes["size"] == "43"
    assert chosen.attributes["colour"] == "black"
    assert lines[0].line_total.amount == Decimal("119.00")


def test_tier3_colour_constraint_changes_selection() -> None:
    result = _run(_shoe_request(size="43", colour="white"))
    assert result.solution is not None
    chosen = next(line.offer for sub in result.solution.sub_baskets for line in sub.lines)
    assert chosen.attributes["colour"] == "white"
    assert chosen.attributes["size"] == "43"


def test_tier3_unavailable_spec_is_infeasible() -> None:
    result = _run(_shoe_request(size="43", colour="red"))
    assert result.solution is None
