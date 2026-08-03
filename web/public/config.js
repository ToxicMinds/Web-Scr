/*
 * Runtime configuration for the read-only dashboard.
 *
 * The dashboard reads the latest optimization run directly from Supabase when
 * a project URL and anon (publishable) key are provided here, applying
 * row-level security on the read-only anon role. When they are absent — or the
 * Supabase tables have not been provisioned yet — it gracefully falls back to
 * the bundled `/data.json` snapshot produced by the nightly pipeline.
 *
 * These are PUBLIC values (anon key only). Never place the service-role key
 * here. On Vercel these can be injected at build time from environment
 * variables; committed defaults stay empty so nothing sensitive is stored.
 */
window.__SUPABASE__ = {
  url: "",
  anonKey: "",
};
