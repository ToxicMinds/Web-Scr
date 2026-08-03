"""Shared constants for scraper plugins (avoids duplicated literals)."""

from __future__ import annotations

# Countries most European supplement retailers ship to and that are relevant to
# a Bratislava (SK) destination. Used as a sensible default `ships_to` set.
EU_SHIPS: frozenset[str] = frozenset({"SK", "CZ", "DE", "PL", "AT", "HU"})
