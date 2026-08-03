"""Report building and generation (Markdown/CSV/Excel/HTML/JSON)."""

from __future__ import annotations

from supplement_optimizer.reports.builder import (
    ReportData,
    build_report_data,
    retailer_rankings,
)
from supplement_optimizer.reports.generators import ReportWriter

__all__ = ["ReportData", "ReportWriter", "build_report_data", "retailer_rankings"]
