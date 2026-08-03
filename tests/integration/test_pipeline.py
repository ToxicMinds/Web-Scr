"""Integration tests for the end-to-end pipeline, reports and CLI."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from supplement_optimizer.cli import app
from supplement_optimizer.domain.enums import ProductCategory
from supplement_optimizer.domain.models import BasketRequest, Requirement
from supplement_optimizer.optimizer.rates import default_rate_provider
from supplement_optimizer.reports import build_report_data
from supplement_optimizer.reports.generators import ReportWriter
from supplement_optimizer.service import OptimizationService

WHEY = ProductCategory.WHEY_PROTEIN.value
CREATINE = ProductCategory.CREATINE_MONOHYDRATE.value


def _target_request() -> BasketRequest:
    return BasketRequest(
        requirements=(
            Requirement(category=WHEY, target_g=Decimal("5000")),
            Requirement(category=CREATINE, target_g=Decimal("2000")),
        ),
        destination_country="SK",
    )


def test_end_to_end_finds_feasible_basket() -> None:
    service = OptimizationService(rate_provider=default_rate_provider())
    result = asyncio.run(service.run(_target_request()))
    assert result.solution is not None
    assert result.solution.total.amount > 0
    # Every requirement is met at or above target.
    assert result.solution.fulfilled_g[WHEY] >= Decimal("5000")
    assert result.solution.fulfilled_g[CREATINE] >= Decimal("2000")
    assert len(result.market.offers) > 20


def test_report_writer_produces_all_formats(tmp_path: Path) -> None:
    rates = default_rate_provider()
    service = OptimizationService(rate_provider=rates)
    result = asyncio.run(service.run(_target_request()))
    data = build_report_data(result, rates)
    paths = ReportWriter(tmp_path).write_all(data)
    for path in paths.values():
        assert path.exists()
    assert (tmp_path / "report.md").read_text().startswith("# Supplement Optimizer Report")
    assert (tmp_path / "report.html").read_text().lstrip().startswith("<!doctype html>")
    assert (tmp_path / "best_basket.json").stat().st_size > 0
    assert (tmp_path / "report.xlsx").stat().st_size > 0


def test_cli_optimize_command_runs() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["optimize", "--whey-kg", "5", "--creatine-kg", "2"])
    assert res.exit_code == 0
    assert "Best basket" in res.stdout


def test_cli_report_command_writes_files(tmp_path: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["report", "--output", str(tmp_path)])
    assert res.exit_code == 0
    assert (tmp_path / "report.md").exists()
