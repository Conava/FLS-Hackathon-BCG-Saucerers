"""Services package for Longevity+ backend.

Exports the two pure-function services used in this slice:
  - compute_vitality  — heuristic Vitality Score engine
  - derive_insights   — risk-flag to human-readable signal translation
"""

from app.services.insights import Insight, derive_insights
from app.services.vitality_engine import (
    DISCLAIMER,
    TrendPoint,
    VitalityResult,
    compute_vitality,
)

__all__ = [
    "DISCLAIMER",
    "TrendPoint",
    "VitalityResult",
    "compute_vitality",
    "Insight",
    "derive_insights",
]
