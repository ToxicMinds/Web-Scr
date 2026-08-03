"""Publish the latest optimization output to Supabase.

Reads the generated ``best_basket.json`` report and upserts it into the
``reports`` table, and records a row in ``optimization_runs`` with its
``basket_items``. Credentials come exclusively from the environment:

    SUPABASE_URL                 e.g. https://<ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY    service-role key (bypasses RLS for writes)

Nothing is hardcoded; if the variables are missing the script exits cleanly
with a non-zero status so CI surfaces the misconfiguration.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

REPORT_PATH = Path(os.environ.get("REPORT_JSON", "artifacts/reports/best_basket.json"))
TIMEOUT = 30.0


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _post(
    client: httpx.Client, url: str, key: str, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    resp = client.post(url, headers=_headers(key), json=rows, timeout=TIMEOUT)
    resp.raise_for_status()
    return list(resp.json())


def main() -> int:
    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base_url or not service_key:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set", file=sys.stderr)
        return 2
    if not REPORT_PATH.exists():
        print(f"report not found: {REPORT_PATH}", file=sys.stderr)
        return 3

    data = json.loads(REPORT_PATH.read_text())
    basket = data["best_basket"]
    rest = f"{base_url}/rest/v1"

    with httpx.Client() as client:
        _post(
            client,
            f"{rest}/reports",
            service_key,
            [
                {
                    "kind": "best_basket",
                    "format": "json",
                    "destination_country": data["destination_country"],
                    "base_currency": data["base_currency"],
                    "generated_at": data["generated_at"],
                    "payload": data,
                }
            ],
        )

        run = _post(
            client,
            f"{rest}/optimization_runs",
            service_key,
            [
                {
                    "request": {"destination_country": data["destination_country"]},
                    "destination_country": data["destination_country"],
                    "base_currency": data["base_currency"],
                    "strategy": basket.get("strategy"),
                    "total_amount": basket["total"]["amount"],
                    "total_currency": basket["total"]["currency"],
                    "shipping_confidence": basket.get("shipping_confidence"),
                    "solution": basket,
                }
            ],
        )
        run_id = run[0]["id"]

        items: list[dict[str, Any]] = []
        for sub in basket["sub_baskets"]:
            for line in sub["lines"]:
                offer = line["offer"]
                items.append(
                    {
                        "optimization_run_id": run_id,
                        "retailer_slug": sub["retailer_slug"],
                        "category_key": offer["category"],
                        "title": offer["title"],
                        "quantity": line["quantity"],
                        "unit_price_amount": line["unit_price"]["amount"],
                        "unit_price_currency": line["unit_price"]["currency"],
                        "line_total_amount": line["line_total"]["amount"],
                        "content_g": line["content_g"],
                    }
                )
        if items:
            _post(client, f"{rest}/basket_items", service_key, items)

    print(f"published report + optimization_run {run_id} with {len(items)} basket items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
