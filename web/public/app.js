/* Read-only Supplement Optimizer dashboard.
 *
 * Data source resolution order:
 *   1. Supabase `reports` table (latest row, anon key + RLS) when configured.
 *   2. Bundled `/data.json` snapshot produced by the nightly pipeline.
 */

const EUR = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" });

function money(m) {
  if (!m) return "—";
  const n = typeof m === "object" ? Number(m.amount) : Number(m);
  const cur = typeof m === "object" ? m.currency : "EUR";
  if (cur === "EUR") return EUR.format(n);
  return `${n.toFixed(2)} ${cur}`;
}

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

async function loadFromSupabase() {
  const cfg = window.__SUPABASE__ || {};
  if (!cfg.url || !cfg.anonKey) return null;
  const endpoint = `${cfg.url}/rest/v1/reports?select=payload&kind=eq.best_basket&order=generated_at.desc&limit=1`;
  try {
    const res = await fetch(endpoint, {
      headers: { apikey: cfg.anonKey, Authorization: `Bearer ${cfg.anonKey}` },
    });
    if (!res.ok) return null;
    const rows = await res.json();
    if (Array.isArray(rows) && rows.length && rows[0].payload) return rows[0].payload;
    return null;
  } catch {
    return null;
  }
}

async function loadData() {
  const remote = await loadFromSupabase();
  if (remote) return { data: remote, source: "Supabase (live)" };
  const res = await fetch("/data.json", { cache: "no-store" });
  const data = await res.json();
  return { data, source: "bundled nightly snapshot" };
}

function renderMeta(data) {
  const meta = document.getElementById("meta");
  const ts = new Date(data.generated_at);
  meta.innerHTML = "";
  meta.append(
    el("span", "chip", `📍 ${data.destination_country}`),
    el("span", "chip", `💶 base ${data.base_currency}`),
    el("span", "chip", `🕒 ${ts.toLocaleString()}`)
  );
}

function renderBasket(app, basket) {
  const section = el("section", "card hero");
  section.append(el("h2", null, "Best Basket"));
  const head = el("div", "hero-head");
  head.append(
    el("div", "big-total", money(basket.total)),
    el(
      "div",
      "hero-tags",
      `<span class="chip">${basket.strategy.replace("_", " ")}</span>` +
        `<span class="chip conf-${basket.shipping_confidence}">shipping: ${basket.shipping_confidence}</span>`
    )
  );
  section.append(head);

  if (basket.fulfilled_g) {
    const f = el("p", "fulfilled");
    f.innerHTML = Object.entries(basket.fulfilled_g)
      .map(([k, v]) => `<b>${(Number(v) / 1000).toFixed(2)} kg</b> ${k.replace(/_/g, " ")}`)
      .join(" &nbsp;·&nbsp; ");
    section.append(f);
  }

  for (const sub of basket.sub_baskets) {
    const box = el("div", "sub");
    box.append(
      el(
        "div",
        "sub-head",
        `<span class="retailer">${sub.retailer_slug}</span>` +
          `<span>${money(sub.total)} <small>(goods ${money(
            sub.product_subtotal
          )}, ship ${money(sub.shipping_cost)})</small></span>`
      )
    );
    const table = el("table", "lines");
    table.innerHTML =
      "<thead><tr><th>Qty</th><th>Product</th><th>Unit</th><th>Line</th></tr></thead>";
    const tb = el("tbody");
    for (const line of sub.lines) {
      const tr = el("tr");
      tr.innerHTML =
        `<td>${line.quantity}×</td>` +
        `<td><a href="${line.offer.url}" target="_blank" rel="noopener">${line.offer.title}</a>` +
        `<span class="cat">${line.offer.category.replace(/_/g, " ")}</span></td>` +
        `<td>${money(line.unit_price)}</td>` +
        `<td>${money(line.line_total)}</td>`;
      tb.append(tr);
    }
    table.append(tb);
    box.append(table);
    section.append(box);
  }
  app.append(section);
}

function renderRankings(app, rankings) {
  if (!rankings || !rankings.length) return;
  const section = el("section", "card");
  section.append(el("h2", null, "Retailer Rankings"));
  const table = el("table", "rank");
  table.innerHTML =
    "<thead><tr><th>#</th><th>Retailer</th><th>Feasible</th><th>Total (EUR)</th><th>Shipping</th></tr></thead>";
  const tb = el("tbody");
  const sorted = [...rankings].sort((a, b) => {
    if (a.feasible !== b.feasible) return a.feasible ? -1 : 1;
    return (a.total_eur ?? 1e9) - (b.total_eur ?? 1e9);
  });
  sorted.forEach((r, i) => {
    const tr = el("tr", r.feasible ? "" : "infeasible");
    tr.innerHTML =
      `<td>${i + 1}</td>` +
      `<td>${r.retailer}</td>` +
      `<td>${r.feasible ? "✅" : "—"}</td>` +
      `<td>${r.total_eur != null ? EUR.format(r.total_eur) : "—"}</td>` +
      `<td><span class="chip conf-${r.shipping_confidence}">${r.shipping_confidence}</span></td>`;
    tb.append(tr);
  });
  table.append(tb);
  section.append(table);
  app.append(section);
}

function renderDownloads(app) {
  const section = el("section", "card");
  section.append(el("h2", null, "Reports & Data"));
  const files = [
    ["report.html", "Full HTML report"],
    ["report.md", "Markdown report"],
    ["report.xlsx", "Excel workbook"],
    ["all_metrics.csv", "All normalized metrics (CSV)"],
    ["cheapest_protein.csv", "Cheapest protein (CSV)"],
    ["cheapest_creatine.csv", "Cheapest creatine (CSV)"],
    ["rankings.csv", "Retailer rankings (CSV)"],
    ["best_basket.json", "Best basket (JSON)"],
  ];
  const ul = el("ul", "downloads");
  for (const [file, label] of files) {
    ul.append(el("li", null, `<a href="/reports/${file}">${label}</a>`));
  }
  section.append(ul);
  app.append(section);
}

async function main() {
  const app = document.getElementById("app");
  try {
    const { data, source } = await loadData();
    renderMeta(data);
    app.innerHTML = "";
    renderBasket(app, data.best_basket);
    renderRankings(app, data.retailer_rankings);
    renderDownloads(app);
    document.getElementById("source-note").textContent = `Data source: ${source} · `;
  } catch (err) {
    app.innerHTML = `<div class="card error">Failed to load report data: ${err}</div>`;
  }
}

main();
