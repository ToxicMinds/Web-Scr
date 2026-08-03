"""Deterministic parser tests for the live Aktin HTML scraper.

Drives the real BeautifulSoup parser against captured markup via an injected
``httpx`` MockTransport -- no network, full coverage of the live path.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

import httpx

from supplement_optimizer.scrapers.aktin import AktinPlugin

WHEY = "whey_protein"
_FIXTURE = Path(__file__).parent.parent / "fixtures" / "aktin_whey.html"


def _mock_aktin() -> AktinPlugin:
    html = _FIXTURE.read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)
    return AktinPlugin(client_factory=lambda: httpx.AsyncClient(transport=transport))


def test_aktin_parses_live_listing_markup() -> None:
    plugin = _mock_aktin()
    offers = asyncio.run(plugin.fetch(WHEY))
    by_size = {int(o.pack_content_g): o for o in offers}
    # The 30 g sample is below MIN_PACK_G and must be dropped.
    assert 30 not in by_size
    assert set(by_size) == {1000, 500}
    grass = by_size[1000]
    assert grass.price.amount == Decimal("35.99")
    assert str(grass.price.currency) == "EUR"
    assert grass.url == "https://aktin.sk/vilgain-grass-fed-whey-protein/cokolada-1-000-g-32051"
    assert grass.flavours == ("Čokoláda",)


def test_aktin_scrape_applies_whey_filter() -> None:
    plugin = _mock_aktin()
    result = asyncio.run(plugin.scrape(WHEY))
    assert result.retailer_slug == "aktin"
    assert result.accepted_count >= 1
    for offer in result.offers:
        assert offer.category == WHEY
        assert offer.url.startswith("https://aktin.sk/")
        assert offer.price.amount > 0
