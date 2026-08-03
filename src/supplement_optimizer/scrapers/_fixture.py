"""Fixture-backed scraper base.

Live web scraping is inherently non-deterministic and site-fragile, which makes
it unsuitable as the default for tests and CI. Every concrete retailer plugin
therefore ships a small, realistic *seed catalog* and extends
:class:`FixtureScraperPlugin`, which turns that catalog into domain
:class:`Offer` objects. The exact same plugin can later fetch live data by
overriding :meth:`fetch` (see :mod:`supplement_optimizer.scrapers.http_base`).

This keeps each retailer a single, self-contained plugin file (metadata +
shipping + coupons + catalog) -- adding a retailer is one new file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import ClassVar

from supplement_optimizer.domain.enums import (
    Availability,
    CouponType,
    CreatineForm,
    Currency,
    ShippingConfidence,
)
from supplement_optimizer.domain.models import (
    Coupon,
    Offer,
    QuantityBreak,
    Retailer,
    ShippingRule,
)
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.plugins.base import ScraperPlugin


@dataclass(frozen=True)
class OfferSpec:
    """Compact, declarative description of one SKU in a plugin's seed catalog."""

    title: str
    pack_content_g: int
    price: str
    path: str
    availability: Availability = Availability.IN_STOCK
    protein_pct: str | None = None
    serving_size_g: str | None = None
    protein_per_serving_g: str | None = None
    flavours: tuple[str, ...] = ()
    creatine_form: CreatineForm | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    quantity_breaks: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class ShippingSpec:
    """Declarative shipping terms for one destination country."""

    destination: str
    cost: str
    free_over: str | None = None
    min_days: int | None = None
    max_days: int | None = None
    methods: tuple[str, ...] = ()
    confidence: ShippingConfidence = ShippingConfidence.DETERMINED


@dataclass(frozen=True)
class CouponSpec:
    """Declarative coupon."""

    code: str
    coupon_type: CouponType
    value: str = "0"
    min_subtotal: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class RetailerSpec:
    """Declarative retailer metadata."""

    slug: str
    name: str
    base_url: str
    home_country: str
    currency: Currency
    ships_to: frozenset[str] = field(default_factory=frozenset)


class FixtureScraperPlugin(ScraperPlugin):
    """A scraper plugin whose offers come from a declarative seed catalog."""

    RETAILER: ClassVar[RetailerSpec]
    SHIPPING: ClassVar[tuple[ShippingSpec, ...]] = ()
    COUPONS: ClassVar[tuple[CouponSpec, ...]] = ()
    CATALOG: ClassVar[dict[str, tuple[OfferSpec, ...]]] = {}

    # ScraperPlugin.slug is bound from the retailer spec in __init_subclass__.
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "RETAILER"):
            cls.slug = cls.RETAILER.slug

    def retailer(self) -> Retailer:
        spec = self.RETAILER
        return Retailer(
            slug=spec.slug,
            name=spec.name,
            base_url=spec.base_url,
            home_country=spec.home_country,
            currency=spec.currency,
            ships_to=spec.ships_to,
        )

    def shipping_rules(self) -> list[ShippingRule]:
        currency = self.RETAILER.currency
        return [
            ShippingRule(
                retailer_slug=self.slug,
                destination_country=s.destination,
                cost=Money(amount=Decimal(s.cost), currency=currency),
                free_threshold=(
                    Money(amount=Decimal(s.free_over), currency=currency)
                    if s.free_over is not None
                    else None
                ),
                methods=s.methods,
                min_delivery_days=s.min_days,
                max_delivery_days=s.max_days,
                confidence=s.confidence,
            )
            for s in self.SHIPPING
        ]

    def coupons(self) -> list[Coupon]:
        currency = self.RETAILER.currency
        return [
            Coupon(
                retailer_slug=self.slug,
                code=c.code,
                coupon_type=c.coupon_type,
                value=Decimal(c.value),
                currency=currency if c.coupon_type is CouponType.FIXED else None,
                min_subtotal=(
                    Money(amount=Decimal(c.min_subtotal), currency=currency)
                    if c.min_subtotal is not None
                    else None
                ),
                expires_at=c.expires_at,
            )
            for c in self.COUPONS
        ]

    def supported_categories(self) -> tuple[str, ...]:
        return tuple(self.CATALOG)

    async def fetch(self, category: str) -> list[Offer]:
        specs = self.CATALOG.get(category, ())
        return [self._to_offer(category, spec) for spec in specs]

    def _to_offer(self, category: str, spec: OfferSpec) -> Offer:
        currency = self.RETAILER.currency
        breaks = tuple(
            QuantityBreak(
                min_quantity=qty, unit_price=Money(amount=Decimal(price), currency=currency)
            )
            for qty, price in spec.quantity_breaks
        )
        return Offer(
            retailer_slug=self.slug,
            category=category,
            title=spec.title,
            brand=self.RETAILER.name,
            url=f"{self.RETAILER.base_url}{spec.path}",
            pack_content_g=Decimal(spec.pack_content_g),
            price=Money(amount=Decimal(spec.price), currency=currency),
            quantity_breaks=breaks,
            availability=spec.availability,
            protein_pct=Decimal(spec.protein_pct) if spec.protein_pct else None,
            serving_size_g=Decimal(spec.serving_size_g) if spec.serving_size_g else None,
            protein_per_serving_g=(
                Decimal(spec.protein_per_serving_g) if spec.protein_per_serving_g else None
            ),
            flavours=spec.flavours,
            creatine_form=spec.creatine_form,
            attributes=dict(spec.attributes),
        )
