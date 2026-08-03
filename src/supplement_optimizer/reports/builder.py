"""Report data builders.

Transforms a :class:`RunResult` into the tabular datasets each report needs.
All heavy lifting uses polars; monetary comparison uses the same engine so
rankings are consistent with the chosen optimum.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import polars as pl

from supplement_optimizer.domain.enums import ProductCategory
from supplement_optimizer.domain.models import BasketRequest
from supplement_optimizer.optimizer import OptimizationEngine, RateProvider, Solution
from supplement_optimizer.service import MarketData, RunResult


@dataclass
class ReportData:
    """Everything the report generators render."""

    generated_at: datetime
    request: BasketRequest
    best: Solution | None
    cheapest_protein: pl.DataFrame
    cheapest_creatine: pl.DataFrame
    retailer_rankings: pl.DataFrame
    all_metrics: pl.DataFrame


def _cheapest_for_category(metrics: pl.DataFrame, category: str, sort_col: str) -> pl.DataFrame:
    if metrics.is_empty():
        return metrics
    subset = metrics.filter(pl.col("category") == category)
    if subset.is_empty() or sort_col not in subset.columns:
        return subset
    return subset.drop_nulls(sort_col).sort(sort_col)


def retailer_rankings(
    request: BasketRequest, market: MarketData, rate_provider: RateProvider
) -> pl.DataFrame:
    """Rank every retailer by the cost of fulfilling the whole basket alone."""
    rows: list[dict[str, object]] = []
    for slug, retailer in market.retailers.items():
        offers = [o for o in market.offers if o.retailer_slug == slug]
        engine = OptimizationEngine(
            retailers={slug: retailer},
            shipping_rules={k: v for k, v in market.shipping_rules.items() if k[0] == slug},
            coupons={slug: market.coupons.get(slug, [])},
            rate_provider=rate_provider,
        )
        solution = engine.optimize(request, offers)
        rows.append(
            {
                "retailer": retailer.name,
                "slug": slug,
                "feasible": solution is not None,
                "total_eur": float(solution.total.amount) if solution else None,
                "shipping_confidence": (str(solution.shipping_confidence) if solution else None),
            }
        )
    frame = pl.DataFrame(rows)
    return frame.sort("total_eur", nulls_last=True) if not frame.is_empty() else frame


def build_report_data(result: RunResult, rate_provider: RateProvider) -> ReportData:
    """Assemble a :class:`ReportData` from a completed run."""
    metrics = result.metrics
    return ReportData(
        generated_at=datetime.now(UTC),
        request=result.request,
        best=result.solution,
        cheapest_protein=_cheapest_for_category(
            metrics, ProductCategory.WHEY_PROTEIN.value, "price_per_100g_protein"
        ),
        cheapest_creatine=_cheapest_for_category(
            metrics, ProductCategory.CREATINE_MONOHYDRATE.value, "price_per_kg"
        ),
        retailer_rankings=retailer_rankings(result.request, result.market, rate_provider),
        all_metrics=metrics,
    )
