"""Typer CLI -- the composition root / entrypoint.

Wires configuration, logging, the plugin registry, the optimization service and
the report writer together. This is the only place that assembles concrete
implementations (Dependency Injection happens here, not in the core).
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer

from supplement_optimizer.config.logging import configure_logging, get_logger
from supplement_optimizer.config.settings import get_settings
from supplement_optimizer.domain.enums import Currency, ProductCategory
from supplement_optimizer.domain.models import BasketRequest, Requirement
from supplement_optimizer.optimizer.rates import default_rate_provider
from supplement_optimizer.plugins.registry import PluginRegistry
from supplement_optimizer.reports import ReportWriter, build_report_data
from supplement_optimizer.service import OptimizationService

app = typer.Typer(
    help="Supplement Optimizer: find the cheapest cross-retailer basket.",
    no_args_is_help=True,
    add_completion=False,
)
_logger = get_logger(__name__)

# Defaults for the flagship problem (5 kg whey + 2 kg creatine to Bratislava).
DEFAULT_WHEY_KG = 5.0
DEFAULT_CREATINE_KG = 2.0
GRAMS_PER_KG = Decimal("1000")


def _build_request(
    whey_kg: float, creatine_kg: float, destination: str, currency: Currency
) -> BasketRequest:
    requirements: list[Requirement] = []
    if whey_kg > 0:
        requirements.append(
            Requirement(
                category=ProductCategory.WHEY_PROTEIN.value,
                target_g=Decimal(str(whey_kg)) * GRAMS_PER_KG,
            )
        )
    if creatine_kg > 0:
        requirements.append(
            Requirement(
                category=ProductCategory.CREATINE_MONOHYDRATE.value,
                target_g=Decimal(str(creatine_kg)) * GRAMS_PER_KG,
            )
        )
    return BasketRequest(
        requirements=tuple(requirements),
        destination_country=destination,
        base_currency=currency,
    )


@app.callback()
def _main() -> None:
    """Initialise logging once for every command."""
    configure_logging()


@app.command("list-retailers")
def list_retailers() -> None:
    """List all registered retailer plugins."""
    registry = PluginRegistry()
    for slug in registry.slugs():
        plugin = registry.create(slug)
        retailer = plugin.retailer()
        typer.echo(
            f"{slug:22s} {retailer.name:22s} {retailer.currency} -> {sorted(retailer.ships_to)}"
        )


@app.command()
def optimize(
    whey_kg: Annotated[float, typer.Option(help="Target whey protein in kg")] = DEFAULT_WHEY_KG,
    creatine_kg: Annotated[float, typer.Option(help="Target creatine in kg")] = DEFAULT_CREATINE_KG,
    destination: Annotated[str | None, typer.Option(help="ISO alpha-2 country")] = None,
    retailer: Annotated[
        list[str] | None, typer.Option(help="Restrict to these retailer slugs")
    ] = None,
) -> None:
    """Find and print the cheapest basket for the requested quantities."""
    settings = get_settings()
    dest = destination or settings.optimizer_destination_country
    request = _build_request(whey_kg, creatine_kg, dest, settings.optimizer_base_currency)

    service = OptimizationService(rate_provider=default_rate_provider())
    result = asyncio.run(service.run(request, retailer_slugs=retailer))

    solution = result.solution
    if solution is None:
        typer.secho("No feasible basket found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(
        f"\nBest basket: {solution.total} ({solution.strategy})", fg=typer.colors.GREEN, bold=True
    )
    for sub in solution.sub_baskets:
        typer.echo(
            f"\n  {sub.retailer_slug}: {sub.total} "
            f"(goods {sub.product_subtotal}, ship {sub.shipping_cost})"
        )
        for line in sub.lines:
            typer.echo(
                f"    {line.quantity} x {line.offer.title} @ {line.unit_price} = {line.line_total}"
            )
    fulfilled = ", ".join(f"{k}: {v} g" for k, v in solution.fulfilled_g.items())
    typer.echo(f"\n  Fulfilled: {fulfilled}")


@app.command()
def report(
    whey_kg: Annotated[float, typer.Option(help="Target whey protein in kg")] = DEFAULT_WHEY_KG,
    creatine_kg: Annotated[float, typer.Option(help="Target creatine in kg")] = DEFAULT_CREATINE_KG,
    destination: Annotated[str | None, typer.Option(help="ISO alpha-2 country")] = None,
    output: Annotated[Path, typer.Option(help="Report output directory")] = Path(
        "artifacts/reports"
    ),
    live_only: Annotated[
        bool,
        typer.Option(
            help="Restrict to retailers with a real live-scraping implementation "
            "(never publish fixture/seed retailers as market data)."
        ),
    ] = False,
) -> None:
    """Run the optimizer and write all report formats to ``output``."""
    settings = get_settings()
    dest = destination or settings.optimizer_destination_country
    request = _build_request(whey_kg, creatine_kg, dest, settings.optimizer_base_currency)

    retailer_slugs = PluginRegistry().live_slugs() if live_only else None
    rates = default_rate_provider()
    service = OptimizationService(rate_provider=rates)
    result = asyncio.run(service.run(request, retailer_slugs=retailer_slugs))
    data = build_report_data(result, rates)
    paths = ReportWriter(output).write_all(data)

    typer.secho(f"Wrote {len(paths)} report files to {output}:", fg=typer.colors.GREEN)
    for name, path in paths.items():
        typer.echo(f"  {name:22s} {path}")


@app.command()
def scrape(
    category: Annotated[list[str] | None, typer.Option(help="Categories to scrape")] = None,
    retailer: Annotated[
        list[str] | None, typer.Option(help="Restrict to these retailer slugs")
    ] = None,
    output: Annotated[
        Path | None, typer.Option(help="Directory to write scraped offers + summary JSON")
    ] = None,
    force: Annotated[
        bool, typer.Option(help="Force a full re-scrape, ignoring any cached offers")
    ] = False,
) -> None:
    """Scrape offers and print a per-retailer summary (no optimization)."""
    categories = category or [
        ProductCategory.WHEY_PROTEIN.value,
        ProductCategory.CREATINE_MONOHYDRATE.value,
    ]
    service = OptimizationService()
    market = asyncio.run(
        service.gather_market_data(categories, retailer_slugs=retailer, force=force)
    )
    typer.echo(f"Scraped {len(market.offers)} offers from {len(market.retailers)} retailers")
    for res in market.scrape_results:
        typer.echo(
            f"  {res.retailer_slug:22s} {res.category:24s} {res.accepted_count}/{res.raw_count}"
        )
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        summary = {
            "categories": categories,
            "retailers": sorted(market.retailers),
            "offer_count": len(market.offers),
            "results": [
                {
                    "retailer_slug": r.retailer_slug,
                    "category": r.category,
                    "accepted": r.accepted_count,
                    "raw": r.raw_count,
                }
                for r in market.scrape_results
            ],
        }
        (output / "scrape_summary.json").write_text(json.dumps(summary, indent=2))
        typer.secho(
            f"Wrote scrape summary to {output / 'scrape_summary.json'}", fg=typer.colors.GREEN
        )


if __name__ == "__main__":
    app()
