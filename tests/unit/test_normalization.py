"""Tests for the normalization engine."""

from __future__ import annotations

from decimal import Decimal

import polars as pl

from supplement_optimizer.domain.enums import Currency
from supplement_optimizer.normalization import normalize_offer, to_frame
from tests.conftest import make_offer


def test_price_per_kg_and_reference_serving() -> None:
    offer = make_offer("a", "whey_protein", 1000, 20)
    norm = normalize_offer(offer)
    assert norm.price_per_kg == Decimal("20")
    # 20 EUR / 1000 g * 25 g = 0.5 EUR per 25 g serving.
    assert norm.price_per_reference_serving == Decimal("0.5")


def test_protein_metrics_from_percentage() -> None:
    offer = make_offer(
        "a",
        "whey_protein",
        1000,
        30,
        protein_pct=Decimal("75"),
        serving_size_g=Decimal("30"),
        protein_per_serving_g=Decimal("24"),
    )
    norm = normalize_offer(offer)
    # 750 g protein per kg; 30 EUR / 750 g * 100 = 4 EUR per 100 g protein.
    assert norm.price_per_100g_protein == Decimal("4")
    assert norm.protein_grams_per_currency == Decimal("25")
    assert norm.cost_per_serving == Decimal("0.9")  # 30/1000*30


def test_cost_over_time_metrics() -> None:
    offer = make_offer("a", "whey_protein", 1000, 30, serving_size_g=Decimal("25"))
    norm = normalize_offer(offer, servings_per_day=Decimal("2"))
    assert norm.cost_per_serving == Decimal("0.75")
    assert norm.cost_per_day == Decimal("1.50")
    assert norm.cost_per_month == Decimal("45.00")
    assert norm.cost_per_year == Decimal("547.50")


def test_creatine_has_no_protein_metrics() -> None:
    offer = make_offer("a", "creatine_monohydrate", 1000, 25)
    norm = normalize_offer(offer)
    assert norm.price_per_100g_protein is None
    assert norm.price_per_kg == Decimal("25")


def test_to_frame_shape_and_columns() -> None:
    offers = [
        make_offer("a", "whey_protein", 1000, 20, protein_pct=Decimal("70")),
        make_offer("b", "creatine_monohydrate", 500, 15, currency=Currency.GBP),
    ]
    frame = to_frame(offers)
    assert isinstance(frame, pl.DataFrame)
    assert frame.height == 2
    assert {"price_per_kg", "price_per_100g_protein", "cost_per_year"} <= set(frame.columns)
    cheapest = frame.sort("price_per_kg").row(0, named=True)
    assert cheapest["retailer"] == "a"
