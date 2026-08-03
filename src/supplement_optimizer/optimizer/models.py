"""Result models produced by the optimization engine.

These are the engine's *output* contract. They are deliberately category-
agnostic: nothing here mentions protein or creatine. A :class:`Solution` is a
set of per-retailer sub-baskets plus a fully-costed total.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from supplement_optimizer.domain.enums import Currency, ShippingConfidence
from supplement_optimizer.domain.models import Offer
from supplement_optimizer.domain.quantities import Money


class BasketLine(BaseModel):
    """A quantity of one offer chosen for the basket."""

    offer: Offer
    quantity: int = Field(..., ge=1)
    unit_price: Money
    line_total: Money
    content_g: Decimal


class RetailerSubBasket(BaseModel):
    """Everything bought from a single retailer within a solution."""

    retailer_slug: str
    lines: tuple[BasketLine, ...]
    product_subtotal: Money
    coupon_code: str | None = None
    coupon_discount: Money
    shipping_cost: Money
    shipping_confidence: ShippingConfidence
    total: Money


class Solution(BaseModel):
    """A fully-costed basket that satisfies every requirement."""

    id: UUID = Field(default_factory=uuid4)
    strategy: str
    currency: Currency
    sub_baskets: tuple[RetailerSubBasket, ...]
    total: Money
    fulfilled_g: dict[str, Decimal]
    shipping_confidence: ShippingConfidence
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def retailer_count(self) -> int:
        """Number of distinct retailers this solution buys from."""
        return len(self.sub_baskets)
