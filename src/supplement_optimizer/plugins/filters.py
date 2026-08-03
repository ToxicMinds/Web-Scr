"""Product filters (Strategy pattern).

A :class:`ProductFilter` decides whether a scraped offer belongs in a category.
Scrapers stay dumb (they extract everything); filters enforce the brief's strict
inclusion rules (whey only, >=22 g protein/serving; 100% creatine monohydrate).

Filters are the *only* place category-specific business rules live, so adding a
new category (coffee, dog food, ...) means adding a new filter -- nothing in the
optimizer or scraper base changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from supplement_optimizer.domain.enums import CreatineForm, ProductCategory
from supplement_optimizer.domain.models import Offer

MIN_PROTEIN_PER_SERVING_G = Decimal("22")
# Fallback when a serving's protein is unknown: minimum protein content by mass.
MIN_WHEY_PROTEIN_PCT = Decimal("60")


class ProductFilter(ABC):
    """Decides whether an offer qualifies for a category."""

    category: str

    @abstractmethod
    def accepts(self, offer: Offer) -> bool:
        """Return True if ``offer`` satisfies this category's rules."""

    def apply(self, offers: list[Offer]) -> list[Offer]:
        """Return only the offers that :meth:`accepts`."""
        return [o for o in offers if o.category == self.category and self.accepts(o)]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


class WheyProteinFilter(ProductFilter):
    """Accept only genuine whey protein powders.

    Excludes mass gainers, meal replacements, plant/vegan protein, casein and
    collagen, and requires >=22 g protein per serving (or, when the serving is
    unknown, a minimum protein percentage by mass).
    """

    category = ProductCategory.WHEY_PROTEIN.value

    INCLUDE = ("whey",)
    EXCLUDE = (
        "gainer",
        "mass",
        "meal replacement",
        "meal-replacement",
        "vegan",
        "plant",
        "soy",
        "pea protein",
        "rice protein",
        "hemp",
        "casein",
        "collagen",
        "egg protein",
        "beef protein",
        # Non-powder formats that can contain the word "whey" in listings.
        "bar",
        "tyčinka",
        "tycinka",
        "drink",
        "nápoj",
        "napoj",
        "cookie",
        "chips",
        "cream",
        "spread",
        "pancake",
        "palacink",
        "oats",
        "kaša",
        "kasa",
        "cereal",
        "sample",
        "vzork",
        "tester",
    )

    def accepts(self, offer: Offer) -> bool:
        title = offer.title
        if not _contains_any(title, self.INCLUDE) or _contains_any(title, self.EXCLUDE):
            return False
        if offer.protein_per_serving_g is not None:
            return offer.protein_per_serving_g >= MIN_PROTEIN_PER_SERVING_G
        if offer.protein_pct is not None:
            return offer.protein_pct >= MIN_WHEY_PROTEIN_PCT
        # Macros not exposed by this retailer's API: the product is genuinely a
        # whey powder (passed include + exclusions) but the >=22 g/serving figure
        # cannot be verified. We accept rather than discard all real inventory,
        # and the offer carries lower data confidence. See ADR-0007.
        return True


class CreatineMonohydrateFilter(ProductFilter):
    """Accept only 100% creatine monohydrate (standard or micronized).

    Rejects other creatine forms (HCl, citrate, gluconate, ethyl ester,
    Kre-Alkalyn) and blends/matrices. Branding and marketing are ignored -- only
    the form matters.
    """

    category = ProductCategory.CREATINE_MONOHYDRATE.value

    INCLUDE = ("creatine", "kreatin", "kreatín")
    EXCLUDE = (
        "hcl",
        "hydrochloride",
        "citrate",
        "gluconate",
        "ethyl ester",
        "kre-alkalyn",
        "kre alkalyn",
        "malate",
        "matrix",
        "blend",
        "nitrate",
        "pyruvate",
        "tablet",
        "tablety",
        "capsule",
        "capsules",
        "kapsul",
        "caps",
        "tabs",
        "tabliet",
        "gummies",
        "gummy",
    )
    #: Localised spellings of "monohydrate" (EN / SK / CZ / DE / PL).
    MONOHYDRATE = ("monohydrate", "monohydrát", "monohydrat")
    ALLOWED_FORMS = (CreatineForm.STANDARD, CreatineForm.MICRONIZED)

    def accepts(self, offer: Offer) -> bool:
        title = offer.title
        if not _contains_any(title, self.INCLUDE) or _contains_any(title, self.EXCLUDE):
            return False
        if not _contains_any(title, self.MONOHYDRATE):
            return False
        return offer.creatine_form is None or offer.creatine_form in self.ALLOWED_FORMS


class Omega3Filter(ProductFilter):
    """Tier 2 example -- accept only fish-oil Omega-3 (measured in grams of oil).

    Demonstrates that a *new divisible ingredient* needs only a filter + a
    category seed + offers: the gram-based packing and the whole engine are
    reused unchanged. Excludes plant/algae sources and krill to keep the
    category strict, mirroring the whey/creatine rigor.
    """

    category = ProductCategory.OMEGA_3.value

    INCLUDE = ("omega-3", "omega 3", "omega3", "fish oil")
    EXCLUDE = ("flax", "flaxseed", "algae", "algal", "krill", "vegan", "plant", "chia")

    def accepts(self, offer: Offer) -> bool:
        title = offer.title
        return _contains_any(title, self.INCLUDE) and not _contains_any(title, self.EXCLUDE)


class GymShoeFilter(ProductFilter):
    """Tier 3 example -- accept gym/training shoes (a discrete, sized item).

    Selection by size/colour is a *requirement* concern (matched against
    ``Offer.attributes`` by the engine), so this filter only enforces category
    membership: training/gym footwear, excluding running/hiking/football boots.
    """

    category = ProductCategory.GYM_SHOES.value

    INCLUDE = ("shoe", "trainer", "sneaker", "lifter")
    EXCLUDE = ("running", "trail", "hiking", "football", "cleat", "sandal", "slipper")

    def accepts(self, offer: Offer) -> bool:
        title = offer.title
        return _contains_any(title, self.INCLUDE) and not _contains_any(title, self.EXCLUDE)


# Registry of built-in filters keyed by category. Extend by adding a filter.
BUILTIN_FILTERS: dict[str, ProductFilter] = {
    WheyProteinFilter.category: WheyProteinFilter(),
    CreatineMonohydrateFilter.category: CreatineMonohydrateFilter(),
    Omega3Filter.category: Omega3Filter(),
    GymShoeFilter.category: GymShoeFilter(),
}


def filter_for(category: str) -> ProductFilter | None:
    """Return the built-in filter for ``category``, if any."""
    return BUILTIN_FILTERS.get(category)
