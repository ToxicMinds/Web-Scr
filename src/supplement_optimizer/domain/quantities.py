"""Money and weight value objects.

Currency-safe, immutable arithmetic on money is the single most common source of
bugs in pricing systems, so it is encapsulated here. All monetary amounts use
:class:`decimal.Decimal` -- never float -- to avoid rounding drift.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from supplement_optimizer.domain.enums import Currency

_CENTS = Decimal("0.01")
_GRAMS_PER_KG = Decimal("1000")


class Money(BaseModel):
    """An immutable monetary amount in a specific currency.

    Arithmetic between :class:`Money` instances requires matching currencies;
    mixing currencies raises :class:`ValueError`. Conversion is an explicit,
    separate concern handled by the exchange-rate layer.
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(...)
    currency: Currency

    @field_validator("amount")
    @classmethod
    def _quantize(cls, value: Decimal) -> Decimal:
        return Decimal(value).quantize(_CENTS, rounding=ROUND_HALF_UP)

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        """Return a zero amount in ``currency``."""
        return cls(amount=Decimal("0"), currency=currency)

    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            msg = f"Cannot combine {self.currency} with {other.currency}"
            raise ValueError(msg)

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, factor: int | Decimal) -> Money:
        return Money(amount=self.amount * Decimal(factor), currency=self.currency)

    __rmul__ = __mul__

    def __lt__(self, other: Money) -> bool:
        self._check(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._check(other)
        return self.amount <= other.amount

    def per(self, quantity: Decimal) -> Decimal:
        """Return the unit amount ``self / quantity`` as a raw Decimal ratio."""
        if quantity == 0:
            msg = "Cannot compute a per-unit price for zero quantity"
            raise ValueError(msg)
        return self.amount / quantity

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


class Weight(BaseModel):
    """An immutable mass, stored canonically in grams."""

    model_config = ConfigDict(frozen=True)

    grams: Decimal = Field(..., ge=0)

    @classmethod
    def from_kg(cls, kg: Decimal | float | int) -> Weight:
        """Construct from kilograms."""
        return cls(grams=Decimal(str(kg)) * _GRAMS_PER_KG)

    @property
    def kg(self) -> Decimal:
        """This weight expressed in kilograms."""
        return self.grams / _GRAMS_PER_KG

    def __add__(self, other: Weight) -> Weight:
        return Weight(grams=self.grams + other.grams)

    def __str__(self) -> str:
        return f"{self.kg} kg"
