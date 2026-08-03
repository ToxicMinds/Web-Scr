"""Aktin scraper plugin (Slovakia, EUR).

Aktin (aktin.sk) is server-rendered HTML (no public GraphQL/JSON API), so it is
scraped with ``httpx`` + BeautifulSoup rather than the Magento base -- see the
ADR log for the httpx-vs-Playwright/GraphQL decision. Category listing pages
carry every field we need as plain markup: product name, the selected pack
size/flavour (``c-product-box__param``) and the price (``c-product-box__price``).

Live scraping is opt-in (``SCRAPER_LIVE``); otherwise the deterministic seed
catalog below is used so tests and CI never depend on the site being reachable.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup, Tag

from supplement_optimizer.domain.enums import Availability, CreatineForm, Currency, ProductCategory
from supplement_optimizer.domain.models import Offer
from supplement_optimizer.domain.quantities import Money
from supplement_optimizer.plugins.registry import register
from supplement_optimizer.scrapers._fixture import OfferSpec, RetailerSpec, ShippingSpec
from supplement_optimizer.scrapers.constants import EU_SHIPS
from supplement_optimizer.scrapers.http_base import HttpScraperPlugin

WHEY = ProductCategory.WHEY_PROTEIN.value
CREATINE = ProductCategory.CREATINE_MONOHYDRATE.value

_WEIGHT_RE = re.compile(r"(\d[\d\s\u00a0]*(?:[.,]\d+)?)\s*(kg|g)\b", re.IGNORECASE)
_PRICE_RE = re.compile(r"(\d[\d\s\u00a0]*(?:[.,]\d+)?)\s*\u20ac")
_GRAMS_PER_KG = Decimal("1000")
#: Minimum pack size (grams) worth listing -- smaller entries are samples.
_MIN_PACK_G = Decimal("100")


def _to_decimal(raw: str) -> Decimal | None:
    cleaned = raw.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _grams(text: str) -> Decimal | None:
    match = _WEIGHT_RE.search(text)
    if not match:
        return None
    amount = _to_decimal(match.group(1))
    if amount is None:
        return None
    grams = amount * _GRAMS_PER_KG if match.group(2).lower() == "kg" else amount
    return grams if grams > 0 else None


def _price(text: str) -> Decimal | None:
    match = _PRICE_RE.search(text)
    return _to_decimal(match.group(1)) if match else None


@register
class AktinPlugin(HttpScraperPlugin):
    """Aktin -- Slovak sports-nutrition retailer (live HTML scraper)."""

    RETAILER = RetailerSpec(
        slug="aktin",
        name="Aktin",
        base_url="https://aktin.sk",
        home_country="SK",
        currency=Currency.EUR,
        ships_to=EU_SHIPS,
    )
    SHIPPING = (
        ShippingSpec(
            "SK", cost="2.99", free_over="49.00", min_days=1, max_days=2, methods=("courier",)
        ),
    )
    #: Category -> listing category slug on aktin.sk.
    CATEGORY_SLUGS = {WHEY: "proteiny", CREATINE: "kreatin-monohydrat"}
    #: Number of listing pages to walk per category. Aktin renders its full
    #: first-page catalog server-side and the ``?strana=`` param only re-serves
    #: page 1 (further items load via XHR), so one request per category suffices.
    PAGES = 1

    CATALOG = {
        WHEY: (
            OfferSpec(
                "Aktin Whey Protein 1000 g",
                1000,
                "22.90",
                "/whey-1000g",
                protein_pct="74",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
            OfferSpec(
                "Aktin Whey Protein 2000 g",
                2000,
                "42.90",
                "/whey-2000g",
                protein_pct="74",
                serving_size_g="30",
                protein_per_serving_g="23",
            ),
        ),
        CREATINE: (
            OfferSpec(
                "Aktin Creatine Monohydrate 500 g",
                500,
                "13.90",
                "/creatine-500g",
                creatine_form=CreatineForm.STANDARD,
            ),
            OfferSpec(
                "Aktin Creatine Monohydrate 1000 g",
                1000,
                "22.90",
                "/creatine-1000g",
                creatine_form=CreatineForm.MICRONIZED,
            ),
        ),
    }

    def listing_urls(self, category: str) -> list[str]:
        slug = self.CATEGORY_SLUGS.get(category)
        if slug is None:
            return []
        base = f"{self.RETAILER.base_url}/{slug}"
        return [base] + [f"{base}?strana={page}" for page in range(2, self.PAGES + 1)]

    def parse(self, category: str, soup: BeautifulSoup, source_url: str) -> list[Offer]:
        offers: list[Offer] = []
        for box in soup.select("div.c-product-box[data-item-name]"):
            offer = self._parse_box(category, box)
            if offer is not None:
                offers.append(offer)
        return offers

    def _parse_box(self, category: str, box: Tag) -> Offer | None:
        link = box.select_one("a.c-product-box__link")
        href = link.get("href") if isinstance(link, Tag) else None
        if not isinstance(href, str):
            return None
        param = box.select_one(".c-product-box__param")
        param_text = param.get_text(" ", strip=True) if param else ""
        grams = _grams(param_text)
        if grams is None or grams < _MIN_PACK_G:
            return None
        price_el = box.select_one(".c-product-box__price--main") or box.select_one(
            ".c-product-box__price"
        )
        price = _price(price_el.get_text(" ", strip=True)) if price_el else None
        if price is None:
            return None
        name = str(box.get("data-item-name") or "").strip()
        # The creatine listing is Aktin's monohydrate-only category
        # (``kreatin-monohydrat``); tile names are often just "Kreatín" /
        # "Creapure®", so annotate the form the source category guarantees.
        if category == CREATINE and "monohydr" not in name.lower():
            name = f"{name} Monohydrát".strip()
        flavour = _WEIGHT_RE.sub("", param_text).strip(" ,\u00a0-\u2013\u2014")
        return Offer(
            retailer_slug=self.slug,
            category=category,
            title=name,
            brand=None,
            url=f"{self.RETAILER.base_url}{href}",
            pack_content_g=grams,
            price=Money(amount=price, currency=Currency.EUR),
            availability=Availability.IN_STOCK,
            flavours=(flavour,) if flavour else (),
        )
