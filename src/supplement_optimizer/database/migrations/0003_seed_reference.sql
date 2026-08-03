-- ============================================================================
-- 0003_seed_reference.sql
-- Idempotent reference data: currencies, countries, categories and the
-- default EUR exchange rates used by the optimizer's StaticRateProvider.
-- ============================================================================

insert into currencies (code, name, symbol) values
  ('EUR', 'Euro', '€'),
  ('GBP', 'Pound Sterling', '£'),
  ('PLN', 'Polish Zloty', 'zł'),
  ('CZK', 'Czech Koruna', 'Kč'),
  ('USD', 'US Dollar', '$'),
  ('HUF', 'Hungarian Forint', 'Ft'),
  ('RON', 'Romanian Leu', 'lei'),
  ('SEK', 'Swedish Krona', 'kr'),
  ('DKK', 'Danish Krone', 'kr')
on conflict (code) do update set name = excluded.name, symbol = excluded.symbol;

insert into countries (iso2, name, default_currency) values
  ('SK', 'Slovakia', 'EUR'),
  ('CZ', 'Czechia', 'CZK'),
  ('PL', 'Poland', 'PLN'),
  ('DE', 'Germany', 'EUR'),
  ('GB', 'United Kingdom', 'GBP'),
  ('HU', 'Hungary', 'HUF'),
  ('RO', 'Romania', 'RON'),
  ('AT', 'Austria', 'EUR'),
  ('SE', 'Sweden', 'SEK'),
  ('DK', 'Denmark', 'DKK'),
  ('PT', 'Portugal', 'EUR')
on conflict (iso2) do update set name = excluded.name, default_currency = excluded.default_currency;

insert into product_categories (key, name, parent_id, filter_slug) values
  ('supplements', 'Supplements', null, null),
  ('whey_protein', 'Whey Protein',
     (select id from product_categories where key = 'supplements'), 'whey_protein'),
  ('creatine_monohydrate', 'Creatine Monohydrate',
     (select id from product_categories where key = 'supplements'), 'creatine_monohydrate')
on conflict (key) do update set name = excluded.name, filter_slug = excluded.filter_slug;

-- Default EUR->quote rates (1 EUR = rate quote), mirroring DEFAULT_EUR_RATES.
insert into exchange_rates (base_code, quote_code, rate, as_of, source) values
  ('EUR', 'EUR', 1.0,   current_date, 'static'),
  ('EUR', 'GBP', 0.85,  current_date, 'static'),
  ('EUR', 'PLN', 4.30,  current_date, 'static'),
  ('EUR', 'CZK', 25.0,  current_date, 'static'),
  ('EUR', 'USD', 1.08,  current_date, 'static'),
  ('EUR', 'HUF', 395.0, current_date, 'static'),
  ('EUR', 'RON', 4.97,  current_date, 'static'),
  ('EUR', 'SEK', 11.30, current_date, 'static'),
  ('EUR', 'DKK', 7.46,  current_date, 'static')
on conflict (base_code, quote_code, as_of) do update set rate = excluded.rate;
