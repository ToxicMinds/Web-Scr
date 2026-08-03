"""Category-agnostic optimization engine."""

from __future__ import annotations

from supplement_optimizer.optimizer.engine import OptimizationEngine
from supplement_optimizer.optimizer.models import (
    BasketLine,
    RetailerSubBasket,
    Solution,
)
from supplement_optimizer.optimizer.packing import PackingResult, cheapest_packing
from supplement_optimizer.optimizer.rates import (
    DEFAULT_EUR_RATES,
    RateProvider,
    StaticRateProvider,
    default_rate_provider,
)

__all__ = [
    "DEFAULT_EUR_RATES",
    "BasketLine",
    "OptimizationEngine",
    "PackingResult",
    "RateProvider",
    "RetailerSubBasket",
    "Solution",
    "StaticRateProvider",
    "cheapest_packing",
    "default_rate_provider",
]
