# Architecture Decision Records

This log records every non-trivial design decision so the reasoning survives as
the project grows. Each record is immutable once accepted; a decision that is
later reversed gets a new record that supersedes the old one (the old record is
kept for history and marked *Superseded*).

Format: **Context → Decision → Consequences**. Records are referenced from the
code by their ID (e.g. `# See ADR-0004`).

---

## ADR-0001: Plugin architecture for retailers and product categories

**Status:** Accepted

**Context.** The platform must support "as many retailers as practical" and,
crucially, arbitrary product categories in the future (coffee, omega-3, dog
food) *without architectural change*. Retailers differ wildly in technology
(Magento GraphQL, server-rendered HTML, JS SPAs) and in how a product's
comparable quantity is defined.

**Decision.** Two independent extension points, both discovered dynamically:

- **Scraper plugins** — one class per retailer, registered via a `@register`
  decorator and auto-discovered by `PluginRegistry`. Adding a retailer means
  adding one file; nothing else changes.
- **Product filter / category plugins** — one `ProductFilter` per category that
  decides which offers qualify and how their comparable quantity is measured.

The optimizer depends on neither: it consumes a generic `Offer` (a price and a
`pack_content_g`) and a generic `Requirement` (a target amount + optional
attribute constraints). It has **no knowledge of supplements**.

**Consequences.** New retailers and new categories are additive. The three
extension "tiers" (new retailer / new category / new attribute-constrained
category) are documented in `docs/EXTENDING.md`. The cost is a small amount of
registry/discovery machinery, judged worthwhile for the stated extensibility
goal.

---

## ADR-0002: polars (not pandas) for normalization

**Status:** Accepted

**Context.** Normalization turns raw offers into comparable metrics (€/kg,
€/100 g protein, cost per serving/day/month/year). This is columnar,
deterministic transformation work.

**Decision.** Use **polars** for tabular normalization.

- Strong, explicit typing and a lazy expression API that keeps transformations
  declarative and side-effect free (a good fit for deterministic pipelines).
- Significantly faster than pandas with a smaller memory footprint, and no
  implicit index semantics to reason about.
- Consistent Decimal/So-typed handling avoids float drift in money math.

**Consequences.** Contributors must know polars' expression API rather than the
more ubiquitous pandas one; considered acceptable given the correctness and
performance benefits. duckdb is used alongside for ad-hoc analytical queries
over historical prices.

---

## ADR-0003: Supabase (Postgres) as the source of truth; Git is not

**Status:** Accepted

**Context.** Prices, history, runs and reports must persist authoritatively and
be queryable; the repository must not be the database.

**Decision.** Supabase (managed Postgres) is the system of record. Schema is
defined as ordered SQL migrations under `database/migrations/`. UUID primary
keys, `created_at/updated_at` timestamps, soft deletes where useful, foreign
keys, indexes and views are used throughout. The dashboard reads the latest run
through the **anon** role (RLS, read-only); writes use the service-role key only
in CI.

**Consequences.** Any environment can be rebuilt by replaying migrations.
Credentials are never committed — they are injected via environment variables /
GitHub Secrets. The dashboard degrades gracefully to a bundled `data.json`
snapshot when Supabase is not configured.

---

## ADR-0004: Exact dynamic-programming packing instead of an MILP solver

**Status:** Accepted

**Context.** For one retailer and one requirement we must find the cheapest
combination of package sizes (e.g. `2 × 2.5 kg`, `5 × 1 kg`, `1 × 5 kg`,
`10 × 500 g`) whose total content lands within the requirement's overshoot
tolerance, honouring bulk quantity-break pricing.

**Decision.** Solve it exactly as a bounded multiple-choice knapsack with a
layered dynamic program over an integer gram grid (one layer per offer). Target
amounts and pack counts are tiny, so the DP is fast, fully deterministic, and
needs **no external MILP/solver dependency**.

**Consequences.** No heavyweight solver (PuLP/OR-Tools) to install, pin or
sandbox; results are reproducible bit-for-bit. Cross-retailer combination and
shipping/coupon/free-shipping-threshold effects are layered on top of this
primitive in the engine (see ADR-0005).

---

## ADR-0005: Deterministic optimizer with explicit strategies

**Status:** Accepted

**Context.** The cheapest basket may come from a single retailer (to clear a
free-shipping threshold) or by splitting across retailers. Shipping, coupons,
VAT and currency conversion all affect the total.

**Decision.** The engine evaluates explicit strategies — single-retailer and
multi-retailer — reusing the ADR-0004 packing primitive, then applies shipping
rules, free-shipping thresholds, coupons and FX conversion to a common base
currency, and picks the minimum total. Everything is pure and deterministic
given the same market snapshot.

**Consequences.** Results are explainable ("why this basket") and testable with
fixed inputs. Adding a new strategy is localized to the engine.

---

## ADR-0006: Scrape via a retailer's structured API where one exists; HTML/Playwright only when forced

**Status:** Accepted

**Context.** Several priority retailers (GymBeam, Bulk, The Protein Works) run
Magento 2, which exposes a structured GraphQL API at `/graphql`. Their public
storefronts are JS-hydrated (Astro/React), so the rendered HTML has no prices
without a browser. Other retailers (e.g. Aktin) render everything server-side.

**Decision.** Prefer the most structured, robust source available per retailer:

1. **Structured API (GraphQL/JSON)** when one exists — implemented once in
   `MagentoGraphQLScraper` and subclassed per Magento retailer. Yields typed
   names, SKUs, per-pack-size variants, prices, currency, stock and bulk tiers.
2. **Server-rendered HTML** via httpx + BeautifulSoup (`HttpScraperPlugin`) when
   there is no API but the markup carries the data (Aktin).
3. **Playwright** only for retailers whose data genuinely requires a real
   browser — reserved, not used by default, because it is far heavier and more
   brittle.

The per-retailer choice is recorded here so the httpx-vs-Playwright question is
never re-litigated blindly.

**Consequences.** Most retailers need no browser, making scraping fast and
deterministic. Live scraping is **opt-in** (`SCRAPER_LIVE`): by default (tests,
CI, local) plugins return a deterministic offline seed catalog, so CI never
depends on third-party availability. A plugin with a real live implementation is
marked `LIVE = True`; reports run with `--live-only` so a seed/fixture retailer
is **never published as real market data**.

---

## ADR-0007: Best-effort protein-macro gating for whey

**Status:** Accepted

**Context.** The whey filter should enforce "≥ 22 g protein per serving" and
"whey only". But the Magento GraphQL APIs do not expose per-serving nutritional
values (the `nutritional_values` field returns empty), so requiring macros would
discard *all* genuinely-valid live whey inventory.

**Decision.** Gate on macros **when they are scrapable**: if per-serving protein
is known it must meet the ≥ 22 g rule; when it is absent, accept the offer as
genuine whey (rather than discard real inventory) and instead strengthen
exclusion of non-whey / non-powder formats (mass gainers, plant/soy/pea, casein,
collagen, bars, drinks, cookies, samples, …, including localized SK/CZ terms).

**Consequences.** Real whey offers are retained while obvious non-whey items are
excluded. If a richer data source later exposes macros, the strict gate applies
automatically. Creatine is constrained analogously: monohydrate only (localized
matching for "monohydrát"), excluding other forms and non-powder formats
(tablets/capsules/gummies) so the powder-by-kg target is met correctly.

---

## ADR-0008: Validate live product URLs before they can enter a basket

**Status:** Accepted

**Context.** A retailer's search index can return products whose storefront page
has since 404'd (observed on GymBeam for delisted third-party SKUs that are
still flagged `IN_STOCK`). Publishing such a link as a "best buy" is misleading
and erodes trust.

**Decision.** In the live path, after building offers, concurrently issue a
liveness check for each unique product URL and drop any offer whose page does
not resolve (`< 400`). Controlled by `scraper_validate_urls` (default on) and
`scraper_validate_concurrency`.

**Consequences.** Every URL that reaches the optimizer — and therefore every URL
published in a report or on the dashboard — resolves. The cost is a bounded set
of extra requests per live run, acceptable for nightly/weekly schedules.
