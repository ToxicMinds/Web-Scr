"""Core domain entities.

Entities are pure data + light invariants (pydantic models). They contain no
I/O, no database access and no knowledge of *how* they are produced. This keeps
the domain independent of frameworks (Clean Architecture: the dependency arrow
points inward, toward this module).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from supplement_optimizer.domain.enums import (
    Availability,
    CouponType,
    CreatineForm,
    Currency,
    ShippingConfidence,
)
from supplement_optimizer.domain.quantities import Money


def _now() -> datetime:
    return datetime.now(UTC)


class Brand(BaseModel):
    """A manufacturer/brand (e.g. GymBeam, Optimum Nutrition)."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    slug: str


class Country(BaseModel):
    """An ISO-3166 country with its default currency and VAT rate."""

    code: str = Field(..., min_length=2, max_length=2, description="ISO alpha-2")
    name: str
    currency: Currency
    vat_rate: Decimal = Field(..., ge=0, le=1, description="Standard VAT as a fraction, e.g. 0.20")


class Retailer(BaseModel):
    """An online store that we scrape and can purchase from."""

    id: UUID = Field(default_factory=uuid4)
    slug: str = Field(..., description="Stable identifier matching the scraper plugin name")
    name: str
    base_url: str
    home_country: str = Field(..., min_length=2, max_length=2)
    currency: Currency
    ships_to: frozenset[str] = Field(default_factory=frozenset)
    active: bool = True

    def ships_to_country(self, country_code: str) -> bool:
        """Whether this retailer delivers to ``country_code``."""
        return country_code in self.ships_to


class ShippingRule(BaseModel):
    """Shipping terms for a retailer -> destination country.

    ``free_threshold`` is the subtotal at or above which shipping is free. A
    ``confidence`` other than ``DETERMINED`` signals the optimizer to treat the
    figures cautiously (see optimizer penalties).
    """

    id: UUID = Field(default_factory=uuid4)
    retailer_slug: str
    destination_country: str = Field(..., min_length=2, max_length=2)
    cost: Money
    free_threshold: Money | None = None
    methods: tuple[str, ...] = ()
    min_delivery_days: int | None = None
    max_delivery_days: int | None = None
    confidence: ShippingConfidence = ShippingConfidence.UNKNOWN


class Coupon(BaseModel):
    """A discount code with its conditions."""

    id: UUID = Field(default_factory=uuid4)
    retailer_slug: str
    code: str
    coupon_type: CouponType
    value: Decimal = Field(default=Decimal("0"), description="Percent (0-1) or fixed amount")
    currency: Currency | None = None
    min_subtotal: Money | None = None
    expires_at: datetime | None = None
    active: bool = True

    def is_valid_at(self, when: datetime) -> bool:
        """Whether the coupon is active and not expired at ``when``."""
        if not self.active:
            return False
        return self.expires_at is None or self.expires_at > when


class QuantityBreak(BaseModel):
    """Bulk pricing: a lower unit price that applies at or above ``min_quantity``."""

    model_config = ConfigDict(frozen=True)

    min_quantity: int = Field(..., ge=1)
    unit_price: Money


class Offer(BaseModel):
    """A single purchasable SKU (one package size) from one retailer.

    ``pack_content_g`` is the amount that counts toward a requirement (net grams
    of product). The optimizer only needs ``category``, ``pack_content_g`` and
    price information; the remaining fields power filtering, normalization and
    reporting.
    """

    id: UUID = Field(default_factory=uuid4)
    retailer_slug: str
    category: str = Field(..., description="Requirement key, e.g. 'whey_protein'")
    title: str
    brand: str | None = None
    url: str

    pack_content_g: Decimal = Field(..., gt=0, description="Net grams of product per package")
    price: Money
    quantity_breaks: tuple[QuantityBreak, ...] = ()
    availability: Availability = Availability.UNKNOWN

    # --- Protein-specific attributes (optional for other categories) ---
    protein_pct: Decimal | None = Field(default=None, ge=0, le=100)
    serving_size_g: Decimal | None = Field(default=None, gt=0)
    protein_per_serving_g: Decimal | None = Field(default=None, ge=0)
    flavours: tuple[str, ...] = ()

    # --- Creatine-specific attributes ---
    creatine_form: CreatineForm | None = None

    # Optional per-offer shipping override (else the retailer rule applies).
    ships_to: frozenset[str] | None = None
    scraped_at: datetime = Field(default_factory=_now)

    def unit_price_for_quantity(self, quantity: int) -> Money:
        """Return the applicable per-package price for buying ``quantity`` units.

        Honours bulk ``quantity_breaks`` (the highest qualifying break wins).
        """
        best = self.price
        for qb in self.quantity_breaks:
            if quantity >= qb.min_quantity and qb.unit_price.amount < best.amount:
                best = qb.unit_price
        return best

    def is_available(self) -> bool:
        """Whether this offer can currently be purchased."""
        return self.availability in (Availability.IN_STOCK, Availability.PREORDER)


class Requirement(BaseModel):
    """A single line of demand in a basket, e.g. 'at least 5000 g of whey'."""

    model_config = ConfigDict(frozen=True)

    category: str
    target_g: Decimal = Field(..., gt=0)
    # Allowed overshoot above target when packing (e.g. 0.2 => up to +20%).
    tolerance: Decimal = Field(default=Decimal("0.25"), ge=0)

    @property
    def max_g(self) -> Decimal:
        """Maximum grams the optimizer may buy for this requirement."""
        return self.target_g * (Decimal("1") + self.tolerance)


class BasketRequest(BaseModel):
    """The full optimization input: what to buy and where to deliver it."""

    requirements: tuple[Requirement, ...]
    destination_country: str = Field(..., min_length=2, max_length=2)
    base_currency: Currency = Currency.EUR
