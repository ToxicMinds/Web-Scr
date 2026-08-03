"""Category-agnostic optimization engine."""

from __future__ import annotations

from supplement_optimizer.optimizer.engine import OptimizationEngine
from supplement_optimizer.optimizer.models import (
    BasketLine,
    RetailerSubBasket,
    Solution,
)
from supplement_optimizer.optimizer.packing import PackingResult, cheapest_packing
from supplement_optimizer.optimizer.rates import RateProvider, StaticRateProvider

__all__ = [
    "BasketLine",
    "OptimizationEngine",
    "PackingResult",
    "RateProvider",
    "RetailerSubBasket",
    "Solution",
    "StaticRateProvider",
    "cheapest_packing",
]
