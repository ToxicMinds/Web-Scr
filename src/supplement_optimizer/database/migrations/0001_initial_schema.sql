-- ============================================================================
-- 0001_initial_schema.sql
-- Supplement Optimizer — core schema.
--
-- Conventions:
--   * UUID primary keys via gen_random_uuid() (pgcrypto / pg core).
--   * created_at / updated_at timestamptz, maintained by triggers.
--   * Soft deletes via nullable deleted_at where records are user-facing.
--   * Foreign keys everywhere; indexes on all FK and hot lookup columns.
--   * Category-agnostic: product_categories is a self-referencing tree, so the
--     same schema serves supplements today and shoes / apparel / groceries
--     tomorrow with zero DDL changes.
-- ============================================================================

create extension if not exists pgcrypto;

-- --- shared updated_at trigger ------------------------------------------------
create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- --- currencies ---------------------------------------------------------------
create table if not exists currencies (
  id          uuid primary key default gen_random_uuid(),
  code        text not null unique check (char_length(code) = 3),
  name        text not null,
  symbol      text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- --- countries ----------------------------------------------------------------
create table if not exists countries (
  id                uuid primary key default gen_random_uuid(),
  iso2              text not null unique check (char_length(iso2) = 2),
  name              text not null,
  default_currency  text references currencies (code) on update cascade,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- --- exchange_rates -----------------------------------------------------------
create table if not exists exchange_rates (
  id          uuid primary key default gen_random_uuid(),
  base_code   text not null references currencies (code) on update cascade,
  quote_code  text not null references currencies (code) on update cascade,
  rate        numeric(18, 8) not null check (rate > 0),
  as_of       date not null default current_date,
  source      text not null default 'static',
  created_at  timestamptz not null default now(),
  unique (base_code, quote_code, as_of)
);
create index if not exists idx_exchange_rates_pair on exchange_rates (base_code, quote_code, as_of desc);

-- --- brands -------------------------------------------------------------------
create table if not exists brands (
  id          uuid primary key default gen_random_uuid(),
  slug        text not null unique,
  name        text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);

-- --- product_categories (self-referencing tree) -------------------------------
create table if not exists product_categories (
  id          uuid primary key default gen_random_uuid(),
  key         text not null unique,
  name        text not null,
  parent_id   uuid references product_categories (id) on delete set null,
  filter_slug text,                       -- which product filter plugin applies
  attributes  jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);
create index if not exists idx_product_categories_parent on product_categories (parent_id);

-- --- retailers ----------------------------------------------------------------
create table if not exists retailers (
  id             uuid primary key default gen_random_uuid(),
  slug           text not null unique,
  name           text not null,
  base_url       text,
  country_iso2   text references countries (iso2) on update cascade,
  currency_code  text references currencies (code) on update cascade,
  scraper_type   text not null default 'http' check (scraper_type in ('http', 'playwright', 'fixture')),
  is_active      boolean not null default true,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  deleted_at     timestamptz
);
create index if not exists idx_retailers_active on retailers (is_active) where deleted_at is null;

-- --- shipping_rules -----------------------------------------------------------
create table if not exists shipping_rules (
  id                        uuid primary key default gen_random_uuid(),
  retailer_id               uuid not null references retailers (id) on delete cascade,
  destination_country       text not null references countries (iso2) on update cascade,
  method                    text not null default 'standard',
  ships                     boolean not null default true,
  cost_amount               numeric(12, 2) not null default 0,
  cost_currency             text not null references currencies (code) on update cascade,
  free_threshold_amount     numeric(12, 2),
  free_threshold_currency   text references currencies (code) on update cascade,
  min_delivery_days         integer,
  max_delivery_days         integer,
  confidence                text not null default 'determined'
                              check (confidence in ('determined', 'estimated', 'unknown')),
  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),
  unique (retailer_id, destination_country, method)
);
create index if not exists idx_shipping_rules_retailer on shipping_rules (retailer_id);
create index if not exists idx_shipping_rules_dest on shipping_rules (destination_country);

-- --- coupons ------------------------------------------------------------------
create table if not exists coupons (
  id                      uuid primary key default gen_random_uuid(),
  retailer_id             uuid not null references retailers (id) on delete cascade,
  code                    text not null,
  type                    text not null check (type in ('percentage', 'fixed', 'free_shipping')),
  value                   numeric(12, 4) not null default 0,
  currency                text references currencies (code) on update cascade,
  min_subtotal_amount     numeric(12, 2),
  min_subtotal_currency   text references currencies (code) on update cascade,
  category_key            text references product_categories (key) on update cascade,
  starts_at               timestamptz,
  expires_at              timestamptz,
  is_active               boolean not null default true,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  deleted_at              timestamptz,
  unique (retailer_id, code)
);
create index if not exists idx_coupons_retailer on coupons (retailer_id);
create index if not exists idx_coupons_active on coupons (is_active) where deleted_at is null;

-- --- products -----------------------------------------------------------------
create table if not exists products (
  id                      uuid primary key default gen_random_uuid(),
  retailer_id             uuid not null references retailers (id) on delete cascade,
  category_id             uuid not null references product_categories (id),
  brand_id                uuid references brands (id) on delete set null,
  external_id             text,
  title                   text not null,
  url                     text not null,
  pack_content_g          numeric(12, 3) not null check (pack_content_g > 0),
  protein_pct             numeric(6, 3),
  serving_size_g          numeric(10, 3),
  protein_per_serving_g   numeric(10, 3),
  creatine_form           text,
  flavours                text[] not null default '{}',
  attributes              jsonb not null default '{}'::jsonb,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  deleted_at              timestamptz,
  unique (retailer_id, url)
);
create index if not exists idx_products_retailer on products (retailer_id);
create index if not exists idx_products_category on products (category_id);
create index if not exists idx_products_brand on products (brand_id);

-- --- prices (current) ---------------------------------------------------------
create table if not exists prices (
  id            uuid primary key default gen_random_uuid(),
  product_id    uuid not null references products (id) on delete cascade,
  amount        numeric(12, 2) not null check (amount >= 0),
  currency      text not null references currencies (code) on update cascade,
  availability  text not null default 'in_stock'
                  check (availability in ('in_stock', 'out_of_stock', 'preorder', 'unknown')),
  scraped_at    timestamptz not null default now(),
  scrape_run_id uuid,
  is_current    boolean not null default true,
  created_at    timestamptz not null default now()
);
create unique index if not exists uq_prices_current on prices (product_id) where is_current;
create index if not exists idx_prices_product on prices (product_id, scraped_at desc);

-- --- historical_prices (append-only log) --------------------------------------
create table if not exists historical_prices (
  id            uuid primary key default gen_random_uuid(),
  product_id    uuid not null references products (id) on delete cascade,
  amount        numeric(12, 2) not null,
  currency      text not null references currencies (code) on update cascade,
  availability  text,
  captured_at   timestamptz not null default now(),
  created_at    timestamptz not null default now()
);
create index if not exists idx_hist_prices_product on historical_prices (product_id, captured_at desc);

-- --- scrape_runs --------------------------------------------------------------
create table if not exists scrape_runs (
  id            uuid primary key default gen_random_uuid(),
  retailer_slug text not null,
  category_key  text,
  status        text not null default 'running'
                  check (status in ('running', 'success', 'failed', 'partial')),
  offers_found  integer not null default 0,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  created_at    timestamptz not null default now()
);
create index if not exists idx_scrape_runs_retailer on scrape_runs (retailer_slug, started_at desc);

-- --- optimization_runs --------------------------------------------------------
create table if not exists optimization_runs (
  id                    uuid primary key default gen_random_uuid(),
  request               jsonb not null,
  destination_country   text not null references countries (iso2) on update cascade,
  base_currency         text not null references currencies (code) on update cascade,
  strategy              text,
  total_amount          numeric(12, 2),
  total_currency        text references currencies (code) on update cascade,
  shipping_confidence   text,
  solution              jsonb,
  started_at            timestamptz not null default now(),
  finished_at           timestamptz,
  created_at            timestamptz not null default now()
);
create index if not exists idx_optimization_runs_created on optimization_runs (created_at desc);

-- --- basket_items -------------------------------------------------------------
create table if not exists basket_items (
  id                    uuid primary key default gen_random_uuid(),
  optimization_run_id   uuid not null references optimization_runs (id) on delete cascade,
  product_id            uuid references products (id) on delete set null,
  retailer_slug         text not null,
  category_key          text not null,
  title                 text not null,
  quantity              integer not null check (quantity > 0),
  unit_price_amount     numeric(12, 2) not null,
  unit_price_currency   text not null references currencies (code) on update cascade,
  line_total_amount     numeric(12, 2) not null,
  content_g             numeric(12, 3) not null,
  created_at            timestamptz not null default now()
);
create index if not exists idx_basket_items_run on basket_items (optimization_run_id);

-- --- reports (public read for the dashboard) ----------------------------------
create table if not exists reports (
  id                    uuid primary key default gen_random_uuid(),
  kind                  text not null,
  format                text not null default 'json',
  destination_country   text,
  base_currency         text,
  generated_at          timestamptz not null default now(),
  payload               jsonb,
  storage_path          text,
  created_at            timestamptz not null default now()
);
create index if not exists idx_reports_kind on reports (kind, generated_at desc);

-- --- scraper_logs -------------------------------------------------------------
create table if not exists scraper_logs (
  id            uuid primary key default gen_random_uuid(),
  scrape_run_id uuid references scrape_runs (id) on delete cascade,
  retailer_slug text,
  level         text not null default 'info',
  event         text not null,
  context       jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now()
);
create index if not exists idx_scraper_logs_run on scraper_logs (scrape_run_id);

-- --- errors -------------------------------------------------------------------
create table if not exists errors (
  id            uuid primary key default gen_random_uuid(),
  source        text not null,
  retailer_slug text,
  message       text not null,
  stack         text,
  context       jsonb not null default '{}'::jsonb,
  occurred_at   timestamptz not null default now(),
  created_at    timestamptz not null default now()
);
create index if not exists idx_errors_source on errors (source, occurred_at desc);

-- --- prices.scrape_run_id FK (added after scrape_runs exists) ------------------
alter table prices
  drop constraint if exists prices_scrape_run_id_fkey,
  add constraint prices_scrape_run_id_fkey
    foreign key (scrape_run_id) references scrape_runs (id) on delete set null;

-- --- updated_at triggers ------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array[
    'currencies','countries','brands','product_categories','retailers',
    'shipping_rules','coupons','products'
  ]
  loop
    execute format(
      'drop trigger if exists trg_%1$s_updated_at on %1$s;
       create trigger trg_%1$s_updated_at before update on %1$s
       for each row execute function set_updated_at();', t
    );
  end loop;
end;
$$;

-- --- views --------------------------------------------------------------------
create or replace view v_current_prices as
select
  p.id            as product_id,
  r.slug          as retailer_slug,
  c.key           as category_key,
  b.name          as brand,
  p.title,
  p.url,
  p.pack_content_g,
  p.protein_pct,
  p.serving_size_g,
  p.protein_per_serving_g,
  p.creatine_form,
  pr.amount       as price_amount,
  pr.currency     as price_currency,
  pr.availability,
  pr.scraped_at
from products p
join retailers r          on r.id = p.retailer_id
join product_categories c on c.id = p.category_id
left join brands b        on b.id = p.brand_id
join prices pr            on pr.product_id = p.id and pr.is_current
where p.deleted_at is null;

create or replace view v_latest_reports as
select distinct on (kind)
  id, kind, format, destination_country, base_currency, generated_at, payload
from reports
order by kind, generated_at desc;

create or replace view v_price_history_stats as
select
  product_id,
  count(*)                       as observations,
  min(amount)                    as lowest_amount,
  max(amount)                    as highest_amount,
  round(avg(amount), 2)          as average_amount,
  max(captured_at)               as last_seen_at
from historical_prices
group by product_id;
