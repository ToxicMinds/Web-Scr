"""Live Magento 2 GraphQL scraper base.

Several target retailers (GymBeam, Bulk, ...) run Magento 2, which exposes a
structured GraphQL API at ``/graphql``. Querying it is dramatically more robust
than scraping JS-hydrated HTML: we get names, SKUs, per-pack-size variants,
prices, currency, stock status, bulk tier prices and canonical URLs as typed
data. See ADR-0006 (GraphQL over HTML/Playwright where an API exists).

The HTTP client is injectable (``client_factory``) so tests drive the real
parser against captured API responses via ``httpx.MockTransport`` -- live code
paths stay fully covered without depending on third-party availability.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from supplement_optimizer.config.logging import get_logger
from supplement_optimizer.config.settings import Settings, get_settings
from supplement_optimizer.domain.enums import Availability, Currency
from supplement_optimizer.domain.models import Offer, QuantityBreak
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.scrapers._fixture import FixtureScraperPlugin

_logger = get_logger(__name__)

ClientFactory = Callable[[], httpx.AsyncClient]

#: Parametrised product query. ``{variants}`` is the retailer's variant field
#: (standard Magento ``variants``; GymBeam exposes ``configurable_variants``).
#: Each variant is a concrete ``SimpleProduct`` (so ``weight`` and ``price_tiers``
#: are directly selectable).
_PRODUCTS_QUERY_TEMPLATE = """
query Products($search: String!, $pageSize: Int!) {{
  products(search: $search, pageSize: $pageSize) {{
    items {{
      __typename
      name
      sku
      url_key
      url_suffix
      stock_status
      price_range {{ minimum_price {{ final_price {{ value currency }} }} }}
      ... on ConfigurableProduct {{
        {variants} {{
          attributes {{ label }}
          product {{
            sku
            name
            weight
            stock_status
            price_range {{ minimum_price {{ final_price {{ value currency }} }} }}
            price_tiers {{ quantity final_price {{ value }} }}
          }}
        }}
      }}
    }}
  }}
}}
""".strip()

_WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b", re.IGNORECASE)
_GRAMS_PER_KG = Decimal("1000")


def grams_from_text(text: str) -> Decimal | None:
    """Extract a net weight in grams from a label like ``'2500 g'`` or ``'2,5 kg'``."""
    match = _WEIGHT_RE.search(text)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", "."))
    except InvalidOperation:
        return None
    unit = match.group(2).lower()
    grams = amount * _GRAMS_PER_KG if unit == "kg" else amount
    return grams if grams > 0 else None


def _availability(stock_status: str | None) -> Availability:
    if stock_status == "IN_STOCK":
        return Availability.IN_STOCK
    if stock_status == "OUT_OF_STOCK":
        return Availability.OUT_OF_STOCK
    return Availability.UNKNOWN


class MagentoGraphQLScraper(FixtureScraperPlugin):
    """Base for retailers scraped via the Magento 2 GraphQL API.

    Concrete plugins declare :attr:`RETAILER`/:attr:`SHIPPING`/:attr:`COUPONS`
    (inherited, declarative metadata) plus :attr:`GRAPHQL_URL` and
    :attr:`SEARCH` (category -> search terms). Extraction is fully generic.
    """

    GRAPHQL_URL: ClassVar[str]
    STORE_HEADER: ClassVar[str | None] = None
    LIVE: ClassVar[bool] = True
    #: Magento variant field name. Standard Magento uses ``variants``; GymBeam's
    #: customised schema exposes ``configurable_variants``.
    VARIANTS_FIELD: ClassVar[str] = "variants"
    #: Category key -> search phrases used to discover candidate products.
    SEARCH: ClassVar[dict[str, tuple[str, ...]]] = {}
    PAGE_SIZE: ClassVar[int] = 24
    BRAND: ClassVar[str | None] = None
    #: Skip variants below this net weight -- these are free samples / testers,
    #: not a purchasable pack that meaningfully contributes to a basket.
    MIN_PACK_G: ClassVar[int] = 100

    def _query(self) -> str:
        return _PRODUCTS_QUERY_TEMPLATE.format(variants=self.VARIANTS_FIELD)

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client_factory = client_factory

    def supported_categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.SEARCH, *self.CATALOG)))

    # -- HTTP -----------------------------------------------------------------

    def _make_client(self) -> httpx.AsyncClient:
        if self._client_factory is not None:
            return self._client_factory()
        headers = {
            "User-Agent": self._settings.scraper_user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.STORE_HEADER:
            headers["store"] = self.STORE_HEADER
        return httpx.AsyncClient(
            headers=headers,
            timeout=self._settings.scraper_request_timeout_seconds,
            follow_redirects=True,
            verify=self._verify(),
        )

    def _verify(self) -> str | bool:
        """Resolve the TLS trust store.

        Honours an explicit ``scraper_ca_bundle`` setting, then ``SSL_CERT_FILE``
        (useful behind a corporate TLS-intercepting proxy); otherwise defaults to
        standard certificate verification (correct in CI/production).
        """
        bundle = self._settings.scraper_ca_bundle or os.environ.get("SSL_CERT_FILE")
        return bundle if bundle else True

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    async def _post(self, client: httpx.AsyncClient, term: str) -> dict[str, Any]:
        response = await client.post(
            self.GRAPHQL_URL,
            json={
                "query": self._query(),
                "variables": {"search": term, "pageSize": self.PAGE_SIZE},
            },
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    async def fetch(self, category: str) -> list[Offer]:
        # Offline/deterministic mode (tests, CI, local default): use the seed
        # catalog. A live path is taken only when explicitly enabled or when a
        # client is injected (parser tests via MockTransport). See ADR-0007.
        if self._client_factory is None and not self._settings.scraper_live:
            return await FixtureScraperPlugin.fetch(self, category)
        terms = self.SEARCH.get(category, ())
        if not terms:
            return []
        offers: dict[tuple[str, Decimal], Offer] = {}
        async with self._make_client() as client:
            for term in terms:
                try:
                    payload = await self._post(client, term)
                except httpx.HTTPError as exc:
                    _logger.warning(
                        "graphql_fetch_failed", retailer=self.slug, term=term, error=str(exc)
                    )
                    continue
                if payload.get("errors"):
                    _logger.warning(
                        "graphql_errors", retailer=self.slug, term=term, errors=payload["errors"]
                    )
                items = (((payload.get("data") or {}).get("products") or {}).get("items")) or []
                for item in items:
                    for offer in self._parse_item(category, item):
                        # One offer per (product page, pack size), keeping the
                        # cheapest flavour/variant -- distinct flavours at the
                        # same size are interchangeable for cost optimisation.
                        key = (offer.url, offer.pack_content_g)
                        existing = offers.get(key)
                        if existing is None or offer.price.amount < existing.price.amount:
                            offers[key] = offer
            resolved = list(offers.values())
            if self._settings.scraper_validate_urls:
                resolved = await self._drop_dead_urls(client, resolved)
        return resolved

    async def _drop_dead_urls(self, client: httpx.AsyncClient, offers: list[Offer]) -> list[Offer]:
        """Keep only offers whose product page actually resolves (<400).

        Search indexes can return stale products whose storefront page 404s
        (observed on GymBeam for delisted third-party SKUs). Validating links
        before they can enter a basket guarantees every published URL resolves.
        """
        urls = {offer.url for offer in offers}
        semaphore = asyncio.Semaphore(self._settings.scraper_validate_concurrency)

        async def check(url: str) -> tuple[str, bool]:
            async with semaphore:
                try:
                    response = await client.get(url)
                except httpx.HTTPError:
                    return url, False
                return url, response.status_code < 400

        results = await asyncio.gather(*(check(url) for url in urls))
        alive = {url for url, ok in results if ok}
        dropped = len(urls) - len(alive)
        if dropped:
            _logger.info("dropped_dead_urls", retailer=self.slug, dropped=dropped, total=len(urls))
        return [offer for offer in offers if offer.url in alive]

    # -- Parsing --------------------------------------------------------------

    def _product_url(self, url_key: str | None, url_suffix: str | None) -> str:
        base = self.RETAILER.base_url.rstrip("/")
        return f"{base}/{url_key or ''}{url_suffix or ''}"

    def _item_url(self, item: dict[str, Any]) -> str:
        """Resolve a product's canonical page URL.

        Default Magento convention is ``{base}/{url_key}{url_suffix}``. Retailers
        with a different routing scheme (e.g. Bulk's ``/products/{slug}/{sku}``)
        override this hook.
        """
        return self._product_url(item.get("url_key"), item.get("url_suffix"))

    def _parse_item(self, category: str, item: dict[str, Any]) -> list[Offer]:
        url = self._item_url(item)
        variants = item.get(self.VARIANTS_FIELD) or item.get("configurable_variants") or []
        if not variants:
            offer = self._simple_offer(category, item, url)
            return [offer] if offer else []
        offers: list[Offer] = []
        for variant in variants:
            offer = self._variant_offer(category, item, variant, url)
            if offer:
                offers.append(offer)
        return offers

    def _simple_offer(self, category: str, item: dict[str, Any], url: str) -> Offer | None:
        title = item.get("name") or ""
        grams = grams_from_text(title)
        price = _final_price(item)
        if grams is None or price is None or grams < self.MIN_PACK_G:
            return None
        amount, currency = price
        return Offer(
            retailer_slug=self.slug,
            category=category,
            title=title,
            brand=self.BRAND,
            url=url,
            pack_content_g=grams,
            price=Money(amount=amount, currency=currency),
            availability=_availability(item.get("stock_status")),
        )

    def _variant_offer(
        self, category: str, item: dict[str, Any], variant: dict[str, Any], url: str
    ) -> Offer | None:
        product = variant.get("product") or {}
        labels = [a.get("label", "") for a in (variant.get("attributes") or [])]
        # Net content must come from the declared pack-size label (or product
        # name), never the shipping ``weight`` which is gross and unreliable
        # (e.g. tablet tubs whose gross weight far exceeds the active grams).
        grams = _grams_from_labels(labels) or grams_from_text(product.get("name") or "")
        price = _final_price(product) or _final_price(item)
        if grams is None or price is None or grams < self.MIN_PACK_G:
            return None
        amount, currency = price
        flavour = _flavour_from_labels(labels, grams)
        return Offer(
            retailer_slug=self.slug,
            category=category,
            title=product.get("name") or item.get("name") or "",
            brand=self.BRAND,
            url=url,
            pack_content_g=grams,
            price=Money(amount=amount, currency=currency),
            quantity_breaks=_tiers(product, currency),
            availability=_availability(product.get("stock_status") or item.get("stock_status")),
            flavours=(flavour,) if flavour else (),
        )


def _final_price(node: dict[str, Any]) -> tuple[Decimal, Currency] | None:
    try:
        fp = node["price_range"]["minimum_price"]["final_price"]
        value = Decimal(str(fp["value"]))
        currency = Currency(fp["currency"])
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return None
    if value <= 0:
        return None
    return value, currency


def _grams_from_labels(labels: list[str]) -> Decimal | None:
    for label in labels:
        grams = grams_from_text(label)
        if grams is not None:
            return grams
    return None


def _flavour_from_labels(labels: list[str], grams: Decimal) -> str | None:
    for label in labels:
        text = label.strip()
        if not text or text.isdigit():
            continue
        if grams_from_text(text) is not None:
            continue
        return text
    return None


def _tiers(product: dict[str, Any], currency: Currency) -> tuple[QuantityBreak, ...]:
    breaks: list[QuantityBreak] = []
    for tier in product.get("price_tiers") or []:
        try:
            qty = int(tier["quantity"])
            value = Decimal(str(tier["final_price"]["value"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
        if qty > 1 and value > 0:
            breaks.append(
                QuantityBreak(min_quantity=qty, unit_price=Money(amount=value, currency=currency))
            )
    return tuple(breaks)
