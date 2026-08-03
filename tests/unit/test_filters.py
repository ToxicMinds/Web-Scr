"""Tests for product filters."""

from __future__ import annotations

from decimal import Decimal

from supplement_optimizer.domain.enums import CreatineForm
from supplement_optimizer.plugins.filters import (
    CreatineMonohydrateFilter,
    WheyProteinFilter,
    filter_for,
)
from tests.conftest import make_offer

WHEY = "whey_protein"
CREATINE = "creatine_monohydrate"


def test_whey_filter_accepts_valid_whey() -> None:
    offer = make_offer(
        "a", WHEY, 1000, 25, protein_pct=Decimal("75"), protein_per_serving_g=Decimal("23")
    )
    offer = offer.model_copy(update={"title": "Impact Whey Protein"})
    assert WheyProteinFilter().accepts(offer)


def test_whey_filter_rejects_gainer_and_plant() -> None:
    f = WheyProteinFilter()
    gainer = make_offer("a", WHEY, 1000, 25, protein_per_serving_g=Decimal("30"))
    gainer = gainer.model_copy(update={"title": "Serious Mass Gainer Whey"})
    vegan = make_offer("a", WHEY, 1000, 25, protein_per_serving_g=Decimal("30"))
    vegan = vegan.model_copy(update={"title": "Vegan Plant Protein"})
    assert not f.accepts(gainer)
    assert not f.accepts(vegan)


def test_whey_filter_rejects_low_protein_serving() -> None:
    offer = make_offer("a", WHEY, 1000, 25, protein_per_serving_g=Decimal("18"))
    offer = offer.model_copy(update={"title": "Whey Protein Light"})
    assert not WheyProteinFilter().accepts(offer)


def test_whey_filter_rejects_when_protein_unknown() -> None:
    offer = make_offer("a", WHEY, 1000, 25)
    offer = offer.model_copy(update={"title": "Whey Protein Mystery"})
    assert not WheyProteinFilter().accepts(offer)


def test_creatine_filter_accepts_monohydrate() -> None:
    offer = make_offer("a", CREATINE, 500, 15, creatine_form=CreatineForm.MICRONIZED)
    offer = offer.model_copy(update={"title": "Creatine Monohydrate 100%"})
    assert CreatineMonohydrateFilter().accepts(offer)


def test_creatine_filter_rejects_other_forms() -> None:
    f = CreatineMonohydrateFilter()
    hcl = make_offer("a", CREATINE, 500, 15)
    hcl = hcl.model_copy(update={"title": "Creatine HCl"})
    plain = make_offer("a", CREATINE, 500, 15)
    plain = plain.model_copy(update={"title": "Creatine Powder"})  # no 'monohydrate'
    assert not f.accepts(hcl)
    assert not f.accepts(plain)


def test_filter_for_returns_none_for_unknown_category() -> None:
    assert filter_for("coffee") is None
    assert filter_for(WHEY) is not None
