"""Tests for the plugin registry and fixture scrapers."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx

from supplement_optimizer.plugins.registry import PluginRegistry
from supplement_optimizer.scrapers.gymbeam import GymBeamPlugin

WHEY = "whey_protein"
CREATINE = "creatine_monohydrate"

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "gymbeam_graphql_whey.json"


def _mock_gymbeam() -> GymBeamPlugin:
    """A live GymBeam plugin whose HTTP client returns a captured GraphQL body.

    This drives the *real* GraphQL parser deterministically (no network), so the
    live extraction code is fully covered without depending on the retailer.
    """
    payload = json.loads(_FIXTURE.read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    return GymBeamPlugin(client_factory=lambda: httpx.AsyncClient(transport=transport))


EXPECTED_SLUGS = {
    "gymbeam",
    "aktin",
    "myprotein",
    "bulk",
    "prozis",
    "nutrend",
    "biotechusa",
    "scitec",
    "bodyworld",
    "amazon_de",
    "amazon_pl",
    "protein_works",
    "sportnahrung_engel",
    "fitness_authority",
}


def test_registry_discovers_all_priority_retailers() -> None:
    registry = PluginRegistry()
    assert set(registry.slugs()) >= EXPECTED_SLUGS


def test_every_plugin_declares_consistent_metadata() -> None:
    registry = PluginRegistry()
    for plugin in registry.create_all():
        retailer = plugin.retailer()
        assert retailer.slug == plugin.slug
        assert retailer.ships_to  # every retailer ships somewhere
        # Shipping rules reference the same slug.
        for rule in plugin.shipping_rules():
            assert rule.retailer_slug == plugin.slug


def test_scrape_applies_product_filter_and_returns_offers() -> None:
    plugin = _mock_gymbeam()
    result = asyncio.run(plugin.scrape(WHEY))
    assert result.retailer_slug == "gymbeam"
    assert result.accepted_count > 0
    assert all(o.category == WHEY for o in result.offers)
    # Prices and pack sizes were parsed from the live GraphQL shape.
    for offer in result.offers:
        assert offer.price.amount > 0
        assert offer.pack_content_g > 0
        assert offer.url.startswith("https://gymbeam.sk/")
        assert offer.url.endswith(".html")
        # Where per-serving protein is known it must meet the >=22 g rule.
        assert offer.protein_per_serving_g is None or offer.protein_per_serving_g >= 22


def test_scrape_parses_pack_sizes_and_prices_from_graphql() -> None:
    plugin = _mock_gymbeam()
    result = asyncio.run(plugin.scrape(WHEY))
    by_size = {int(o.pack_content_g): o for o in result.offers}
    # The captured True Whey fixture has 1000 g @ 33.95 and 2500 g @ 79.95.
    assert by_size[1000].price.amount == Decimal("33.95")
    assert by_size[2500].price.amount == Decimal("79.95")
    assert str(by_size[1000].price.currency) == "EUR"


def test_scrape_creatine_only_returns_monohydrate() -> None:
    registry = PluginRegistry()
    plugin = registry.create("biotechusa")
    result = asyncio.run(plugin.scrape(CREATINE))
    assert result.accepted_count > 0
    for offer in result.offers:
        assert "monohydrate" in offer.title.lower()


def test_create_unknown_slug_raises() -> None:
    registry = PluginRegistry()
    try:
        registry.create("does_not_exist")
    except KeyError as exc:
        assert "does_not_exist" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")
