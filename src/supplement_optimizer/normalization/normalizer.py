"""Normalization: turn raw offers into *comparable* per-unit metrics.

The golden rule from the brief: **never compare raw package prices**. A 1 kg tub
at 25 EUR and a 2.27 kg tub at 45 EUR are only comparable once reduced to a
common basis (EUR/kg, EUR per 100 g protein, cost per serving, ...).

Two public surfaces:

* :func:`normalize_offer` -- pure, per-offer computation returning a
  :class:`NormalizedOffer` (used by the reporting/optimization layers).
* :func:`to_frame` -- vectorised construction of a :class:`polars.DataFrame`
  for analytics, ranking and export. polars is used (over pandas) for its strict
  typing, speed and expression API; see ADR-0002.
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl
from pydantic import BaseModel

from supplement_optimizer.domain.models import Offer

# Consumption assumptions used to derive cost-over-time metrics. These are
# constants (no magic numbers scattered in code) and can be overridden per call.
DEFAULT_SERVINGS_PER_DAY = Decimal("1")
DAYS_PER_MONTH = Decimal("30")
DAYS_PER_YEAR = Decimal("365")
REFERENCE_SERVING_G = Decimal("25")  # the "€/25 g serving" reference basis
GRAMS_PER_KG = Decimal("1000")
GRAMS_PER_100 = Decimal("100")


class NormalizedOffer(BaseModel):
    """An offer plus every derived, comparable metric.

    Currency-bearing metrics are stored as raw :class:`~decimal.Decimal` ratios
    in the offer's own currency; cross-currency comparison happens after the
    optimizer converts to a base currency. Metrics that cannot be computed for a
    category (e.g. protein metrics for creatine) are ``None``.
    """

    offer: Offer

    price_per_kg: Decimal
    price_per_reference_serving: Decimal
    cost_per_serving: Decimal | None = None
    cost_per_day: Decimal | None = None
    cost_per_month: Decimal | None = None
    cost_per_year: Decimal | None = None

    # Protein-specific.
    price_per_100g_protein: Decimal | None = None
    protein_grams_per_currency: Decimal | None = None
    protein_per_serving_g: Decimal | None = None

    # Generic content efficiency (grams of product per currency unit).
    grams_per_currency: Decimal | None = None


def normalize_offer(
    offer: Offer, *, servings_per_day: Decimal = DEFAULT_SERVINGS_PER_DAY
) -> NormalizedOffer:
    """Compute all comparable metrics for a single ``offer``."""
    price = offer.price.amount
    content = offer.pack_content_g

    price_per_kg = (price / content) * GRAMS_PER_KG
    price_per_reference_serving = (price / content) * REFERENCE_SERVING_G
    grams_per_currency = content / price if price > 0 else None

    result = NormalizedOffer(
        offer=offer,
        price_per_kg=price_per_kg,
        price_per_reference_serving=price_per_reference_serving,
        grams_per_currency=grams_per_currency,
    )

    # Serving-based cost metrics (any category that declares a serving size).
    if offer.serving_size_g and offer.serving_size_g > 0:
        cost_per_serving = (price / content) * offer.serving_size_g
        result.cost_per_serving = cost_per_serving
        cost_per_day = cost_per_serving * servings_per_day
        result.cost_per_day = cost_per_day
        result.cost_per_month = cost_per_day * DAYS_PER_MONTH
        result.cost_per_year = cost_per_day * DAYS_PER_YEAR

    # Protein-specific metrics.
    total_protein_g = _total_protein_grams(offer)
    if total_protein_g and total_protein_g > 0:
        result.price_per_100g_protein = (price / total_protein_g) * GRAMS_PER_100
        result.protein_grams_per_currency = total_protein_g / price if price > 0 else None
        result.protein_per_serving_g = offer.protein_per_serving_g

    return result


def _total_protein_grams(offer: Offer) -> Decimal | None:
    """Best estimate of total protein grams in a package.

    Prefers protein percentage (most reliable); falls back to
    ``serving count * protein per serving``.
    """
    if offer.protein_pct is not None:
        return offer.pack_content_g * (offer.protein_pct / Decimal("100"))
    if offer.serving_size_g and offer.protein_per_serving_g:
        servings = offer.pack_content_g / offer.serving_size_g
        return servings * offer.protein_per_serving_g
    return None


def to_frame(
    offers: list[Offer], *, servings_per_day: Decimal = DEFAULT_SERVINGS_PER_DAY
) -> pl.DataFrame:
    """Build a polars DataFrame of normalized metrics for analytics/reporting."""
    rows: list[dict[str, object]] = []
    for offer in offers:
        norm = normalize_offer(offer, servings_per_day=servings_per_day)
        rows.append(
            {
                "retailer": offer.retailer_slug,
                "category": offer.category,
                "title": offer.title,
                "brand": offer.brand,
                "currency": str(offer.price.currency),
                "pack_content_g": float(offer.pack_content_g),
                "price": float(offer.price.amount),
                "price_per_kg": float(norm.price_per_kg),
                "price_per_reference_serving": float(norm.price_per_reference_serving),
                "price_per_100g_protein": _opt_float(norm.price_per_100g_protein),
                "protein_grams_per_currency": _opt_float(norm.protein_grams_per_currency),
                "cost_per_serving": _opt_float(norm.cost_per_serving),
                "cost_per_month": _opt_float(norm.cost_per_month),
                "cost_per_year": _opt_float(norm.cost_per_year),
                "availability": str(offer.availability),
                "url": offer.url,
            }
        )
    return pl.DataFrame(rows)


def _opt_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
