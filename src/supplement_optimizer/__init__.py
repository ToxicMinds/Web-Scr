"""Supplement Optimizer: a plugin-based procurement optimization platform.

The package is layered (Clean Architecture):

``domain``            Pure entities + value objects (no I/O).
``normalization``     Turns raw offers into comparable per-unit metrics.
``optimizer``         Category-agnostic cheapest-basket engine.
``plugins``           Plugin contracts, registry and product filters.
``scrapers``          Concrete retailer plugins (offline fixtures + live).
``database``          Supabase persistence + repositories + SQL migrations.
``reports``           Report generators (Markdown/CSV/Excel/HTML).
``config``            Settings (pydantic-settings) and structured logging.
``cli``               Typer entrypoint / composition root.
"""

from __future__ import annotations

__version__ = "0.1.0"
