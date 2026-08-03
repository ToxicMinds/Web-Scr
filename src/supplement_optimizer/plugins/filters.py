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
    )

    def accepts(self, offer: Offer) -> bool:
        title = offer.title
        if not _contains_any(title, self.INCLUDE) or _contains_any(title, self.EXCLUDE):
            return False
        if offer.protein_per_serving_g is not None:
            return offer.protein_per_serving_g >= MIN_PROTEIN_PER_SERVING_G
        if offer.protein_pct is not None:
            return offer.protein_pct >= MIN_WHEY_PROTEIN_PCT
        # Neither figure available -> cannot verify the minimum: reject.
        return False


class CreatineMonohydrateFilter(ProductFilter):
    """Accept only 100% creatine monohydrate (standard or micronized).

    Rejects other creatine forms (HCl, citrate, gluconate, ethyl ester,
    Kre-Alkalyn) and blends/matrices. Branding and marketing are ignored -- only
    the form matters.
    """

    category = ProductCategory.CREATINE_MONOHYDRATE.value

    INCLUDE = ("creatine",)
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
    )
    ALLOWED_FORMS = (CreatineForm.STANDARD, CreatineForm.MICRONIZED)

    def accepts(self, offer: Offer) -> bool:
        title = offer.title
        if not _contains_any(title, self.INCLUDE) or _contains_any(title, self.EXCLUDE):
            return False
        if "monohydrate" not in title.lower():
            return False
        return offer.creatine_form is None or offer.creatine_form in self.ALLOWED_FORMS


# Registry of built-in filters keyed by category. Extend by adding a filter.
BUILTIN_FILTERS: dict[str, ProductFilter] = {
    WheyProteinFilter.category: WheyProteinFilter(),
    CreatineMonohydrateFilter.category: CreatineMonohydrateFilter(),
}


def filter_for(category: str) -> ProductFilter | None:
    """Return the built-in filter for ``category``, if any."""
    return BUILTIN_FILTERS.get(category)
