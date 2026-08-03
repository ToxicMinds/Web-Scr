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
  url: "https://agbkqfylsoqqpntoxthk.supabase.co",
  anonKey:
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFnYmtxZnlsc29xcXBudG94dGhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU3NjQ0OTQsImV4cCI6MjEwMTM0MDQ5NH0.4x0ot8pzZFC975cPcRhK8K0i5-xa86-gnPH5Oy7V0m0",
};
