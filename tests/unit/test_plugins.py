"""Tests for the plugin registry and fixture scrapers."""

from __future__ import annotations

import asyncio

from supplement_optimizer.plugins.registry import PluginRegistry

WHEY = "whey_protein"
CREATINE = "creatine_monohydrate"

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
    registry = PluginRegistry()
    plugin = registry.create("gymbeam")
    result = asyncio.run(plugin.scrape(WHEY))
    assert result.retailer_slug == "gymbeam"
    assert result.accepted_count > 0
    assert all(o.category == WHEY for o in result.offers)
    # All accepted whey offers meet the >=22 g/serving rule (or pct fallback).
    for offer in result.offers:
        assert offer.protein_per_serving_g is None or offer.protein_per_serving_g >= 22


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
