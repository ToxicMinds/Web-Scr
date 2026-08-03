"""Normalization of offers into comparable per-unit metrics."""

from __future__ import annotations

from supplement_optimizer.normalization.normalizer import (
    NormalizedOffer,
    normalize_offer,
    to_frame,
)

__all__ = ["NormalizedOffer", "normalize_offer", "to_frame"]
