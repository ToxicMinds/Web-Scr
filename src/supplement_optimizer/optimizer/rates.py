"""Currency conversion abstraction used by the optimizer.

The engine costs everything in a single *base currency*. Conversion is isolated
behind :class:`RateProvider` (Strategy pattern) so it can be backed by a static
table (tests, offline) or by the ``exchange_rates`` table (production) without
touching the engine.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from supplement_optimizer.domain.enums import Currency
from supplement_optimizer.domain.quantities import Money


class RateProvider(Protocol):
    """Converts monetary amounts into a base currency."""

    def rate(self, source: Currency, target: Currency) -> Decimal:
        """Return units of ``target`` per one unit of ``source``."""
        ...

    def convert(self, amount: Money, target: Currency) -> Money:
        """Convert ``amount`` into ``target`` currency."""


class StaticRateProvider:
    """A deterministic rate provider backed by an in-memory table.

    Rates are expressed relative to a single pivot currency (EUR by default),
    which keeps the table small and cross-rates consistent.
    """

    def __init__(self, per_eur: dict[Currency, Decimal], pivot: Currency = Currency.EUR) -> None:
        self._pivot = pivot
        self._per_eur = {pivot: Decimal("1"), **per_eur}

    def rate(self, source: Currency, target: Currency) -> Decimal:
        if source == target:
            return Decimal("1")
        try:
            src = self._per_eur[source]
            tgt = self._per_eur[target]
        except KeyError as exc:  # pragma: no cover - defensive
            msg = f"No exchange rate available for {exc.args[0]}"
            raise ValueError(msg) from exc
        return tgt / src

    def convert(self, amount: Money, target: Currency) -> Money:
        return Money(amount=amount.amount * self.rate(amount.currency, target), currency=target)
