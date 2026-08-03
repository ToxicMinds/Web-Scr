-- ============================================================================
-- 0002_rls.sql
-- Row-level security. The dashboard uses the anon (publishable) key, so anon
-- gets read-only SELECT on the public-facing tables. All writes happen from
-- the pipeline using the service-role key, which bypasses RLS entirely.
-- ============================================================================

do $$
declare
  t text;
begin
  foreach t in array array[
    'reports','optimization_runs','basket_items','retailers','countries',
    'currencies','product_categories','shipping_rules','coupons',
    'products','prices','historical_prices','scrape_runs','exchange_rates','brands'
  ]
  loop
    execute format('alter table %I enable row level security;', t);
    execute format('drop policy if exists "anon_read_%1$s" on %1$I;', t);
    execute format(
      'create policy "anon_read_%1$s" on %1$I for select to anon using (true);', t
    );
  end loop;
end;
$$;

-- scraper_logs and errors are operational/internal: no anon access (RLS on,
-- no policy => anon sees nothing; service role still bypasses).
alter table scraper_logs enable row level security;
alter table errors enable row level security;
