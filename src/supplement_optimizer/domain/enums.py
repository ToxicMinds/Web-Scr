"""Enumerations shared across the domain.

These are intentionally free of behaviour: they describe *what* a thing is, not
*how* it is processed. Keeping categories as string-backed enums lets the
optimizer stay category-agnostic (it treats a category as an opaque key) while
still giving the scraping/filtering layer well-known constants to target.
"""

from __future__ import annotations

from enum import StrEnum


class Currency(StrEnum):
    """ISO-4217 currency codes relevant to European retailers."""

    EUR = "EUR"
    GBP = "GBP"
    PLN = "PLN"
    CZK = "CZK"
    USD = "USD"
    HUF = "HUF"
    RON = "RON"
    SEK = "SEK"
    DKK = "DKK"


class ProductCategory(StrEnum):
    """Well-known product categories.

    The optimizer never imports this enum: it operates on arbitrary category
    keys. New categories (coffee, dog food, ...) can be added here for the
    scraping/filtering layer without any optimizer change.
    """

    WHEY_PROTEIN = "whey_protein"
    CREATINE_MONOHYDRATE = "creatine_monohydrate"
    # Tier 2 example: another divisible supplement (measured in grams of oil).
    OMEGA_3 = "omega_3"
    # Tier 3 example: a discrete, sized item (measured in units/pairs).
    GYM_SHOES = "gym_shoes"


class Availability(StrEnum):
    """Whether an offer can currently be purchased."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class ShippingConfidence(StrEnum):
    """How the shipping figures for a rule were obtained.

    The brief mandates: *do not estimate shipping* -- capture it. When it truly
    cannot be determined we record it explicitly rather than silently guessing.
    """

    DETERMINED = "determined"  # read directly from the retailer
    ESTIMATED = "estimated"  # derived/heuristic -- penalised by the optimizer
    UNKNOWN = "unknown"  # could not be determined at all


class CouponType(StrEnum):
    """Kinds of discount a coupon can apply."""

    PERCENT = "percent"  # e.g. 10% off subtotal
    FIXED = "fixed"  # e.g. 5 EUR off
    FREE_SHIPPING = "free_shipping"  # waive shipping cost


class CreatineForm(StrEnum):
    """Accepted physical forms of creatine monohydrate."""

    STANDARD = "standard"
    MICRONIZED = "micronized"
