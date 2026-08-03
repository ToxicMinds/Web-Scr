"""Concrete retailer scraper plugins.

Each module registers exactly one :class:`~supplement_optimizer.plugins.base.ScraperPlugin`
via the ``@register`` decorator. The :class:`PluginRegistry` imports every module
in this package to discover them, so adding a retailer = adding one module here.
"""

from __future__ import annotations
