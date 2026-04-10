"""Vitality Score engine — heuristic v2.

NON-CLINICAL DISCLAIMER
=======================
The weights, thresholds, and sub-score formulas below are heuristic
approximations intended for a wellness-framed product demo.  They are
*not* clinically validated, peer-reviewed, or endorsed by any medical
body.  All outputs carry the DISCLAIMER constant and must be presented
as "wellness signals, not medical advice."

Formula source of truth: ``docs/10-vitality-formula.md``.

Sub-score weights (composite):
  sleep      = 0.20
  activity   = 0.20
  metabolic  = 0.20
  cardio     = 0.25
  lifestyle  = 0.15

These weights were chosen to align with the BCG brief's longevity
dimensions and will be retrained on outcomes data in v2.

Wearable window constants:
  SCORING_WINDOW_DAYS = 7   — used to compute current sub-scores
  TREND_WINDOW_DAYS   = 30  — used to build the sparkline trend array

Sub-score functions receive a pre-sliced list of ``WearableDay`` objects
no longer than ``SCORING_WINDOW_DAYS``.  ``compute_vitality`` handles the
slicing so callers may pass the full available history.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DISCLAIMER: str = "Wellness signal, not medical advice."

# Days of wearable history used for subscore computation
SCORING_WINDOW_DAYS: int = 7

# Days of wearable history used for the trend sparkline
TREND_WINDOW_DAYS: int = 30

# Composite weights — must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "sleep": 0.20,
    "activity": 0.20,
    "metabolic": 0.20,
    "cardio": 0.25,
    "lifestyle": 0.15,
}

# ---------------------------------------------------------------------------
# Piecewise-linear interpolation primitive
# ---------------------------------------------------------------------------


def _lerp(anchors: list[tuple[float, float]], x: float) -> float:
    """Piecewise-linear interpolation over a sorted anchor table.

    Parameters
    ----------
    anchors:
        Non-empty list of ``(input_value, output_score)`` pairs sorted
        ascending by input_value.
    x:
        The input value to evaluate.

    Returns
    -------
    float
        The interpolated output.  Clamps to the first/last output value
        when ``x`` is outside the anchor range.
    """
    if x <= anchors[0][0]:
        return anchors[0][1]
    if x >= anchors[-1][0]:
        return anchors[-1][1]
    for i in range(len(anchors) - 1):
        lo_x, lo_y = anchors[i]
        hi_x, hi_y = anchors[i + 1]
        if lo_x <= x < hi_x:
            f = (x - lo_x) / (hi_x - lo_x)
            return lo_y + f * (hi_y - lo_y)
    # Should be unreachable given the above clamping, but keeps mypy happy.
    return anchors[-1][1]


# ---------------------------------------------------------------------------
# Anchor tables (from docs/10-vitality-formula.md)
# ---------------------------------------------------------------------------

_SLEEP_DURATION_ANCHORS: list[tuple[float, float]] = [
    (4.0, 20.0),
    (6.0, 55.0),
    (7.5, 95.0),
    (9.0, 80.0),
    (10.0, 55.0),
]

_ACTIVE_MINUTES_ANCHORS: list[tuple[float, float]] = [
    (0.0, 10.0),
    (75.0, 50.0),
    (150.0, 85.0),
    (300.0, 100.0),
]

_STEPS_ANCHORS: list[tuple[float, float]] = [
    (2000.0, 20.0),
    (5000.0, 55.0),
    (8000.0, 85.0),
    (12000.0, 100.0),
]

_HBA1C_ANCHORS: list[tuple[float, float]] = [
    (5.0, 100.0),
    (5.7, 85.0),
    (6.4, 55.0),
    (7.5, 30.0),
    (9.0, 10.0),
]

_GLUCOSE_ANCHORS: list[tuple[float, float]] = [
    (4.5, 100.0),
    (5.6, 85.0),
    (6.9, 55.0),
    (9.0, 25.0),
]

_CRP_ANCHORS: list[tuple[float, float]] = [
    (0.5, 100.0),
    (1.0, 90.0),
    (3.0, 60.0),
    (10.0, 30.0),
]

_SBP_ANCHORS: list[tuple[float, float]] = [
    (110.0, 100.0),
    (120.0, 90.0),
    (130.0, 70.0),
    (140.0, 45.0),
    (160.0, 15.0),
]

_LDL_ANCHORS: list[tuple[float, float]] = [
    (2.0, 100.0),
    (2.6, 85.0),
    (3.3, 60.0),
    (4.1, 35.0),
    (5.0, 15.0),
]

_RESTING_HR_ANCHORS: list[tuple[float, float]] = [
    (55.0, 100.0),
    (60.0, 90.0),
    (70.0, 75.0),
    (80.0, 55.0),
    (90.0, 30.0),
]

_EXERCISE_ANCHORS: list[tuple[float, float]] = [
    (0.0, 30.0),
    (2.0, 65.0),
    (4.0, 90.0),
    (6.0, 100.0),
]

_STRESS_ANCHORS: list[tuple[float, float]] = [
    (1.0, 100.0),
    (5.0, 60.0),
    (10.0, 20.0),
]

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TrendPoint:
    """A single point on the vitality trend sparkline."""

    date: datetime.date
    score: float


@dataclass
class VitalityResult:
    """Computed vitality result — all fields are wellness-framed."""

    score: float  # 0–100 composite weighted average of sub-scores
    subscores: dict[str, float]  # {"sleep","activity","metabolic","cardio","lifestyle"}
    risk_flags: list[str]  # short flag codes, see module-level comment
    trend: list[TrendPoint]  # per-day sleep+activity score, newest day first
    disclaimer: str = field(default=DISCLAIMER)  # always DISCLAIMER


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def _sleep_subscore(wearable: list[WearableDay]) -> float:
    """Sleep & Recovery sub-score (0–100).

    Algorithm (docs/10-vitality-formula.md §2.1):
    1. Compute duration_score via lerp on sleep_duration_hrs.
    2. If sleep_quality_score is available, average with duration_score.
    3. If 7-day mean deep_sleep_pct >= 20%, add +5 bonus then clamp.
    """
    if not wearable:
        return 50.0

    # Per-day: compute quality_avg (duration lerp, optionally averaged with quality score)
    per_day_scores: list[float] = []
    for day in wearable:
        if day.sleep_duration_hrs is None:
            continue
        duration_score = _lerp(_SLEEP_DURATION_ANCHORS, day.sleep_duration_hrs)
        if day.sleep_quality_score is not None:
            quality_avg = (duration_score + day.sleep_quality_score) / 2.0
        else:
            quality_avg = duration_score
        per_day_scores.append(quality_avg)

    if not per_day_scores:
        return 50.0

    base_score = sum(per_day_scores) / len(per_day_scores)

    # Deep sleep bonus: apply if 7-day mean >= 20%
    deep_vals = [d.deep_sleep_pct for d in wearable if d.deep_sleep_pct is not None]
    if deep_vals and (sum(deep_vals) / len(deep_vals)) >= 20.0:
        base_score += 5.0

    return _clamp(base_score)


def _activity_subscore(wearable: list[WearableDay]) -> float:
    """Activity sub-score (0–100).

    Algorithm (docs/10-vitality-formula.md §2.2):
    1. Sum active_minutes over window; scale to 7-day equivalent; lerp.
    2. Average daily steps; lerp.
    3. Return mean of whichever components are available.
    """
    if not wearable:
        return 30.0

    n = len(wearable)
    components: list[float] = []

    # Active-minutes component
    minutes_vals = [d.active_minutes for d in wearable if d.active_minutes is not None]
    if minutes_vals:
        total_mins = sum(minutes_vals)
        weekly_mins = total_mins * (7.0 / n)
        components.append(_lerp(_ACTIVE_MINUTES_ANCHORS, weekly_mins))

    # Steps component
    steps_vals = [d.steps for d in wearable if d.steps is not None]
    if steps_vals:
        avg_steps = sum(steps_vals) / len(steps_vals)
        components.append(_lerp(_STEPS_ANCHORS, avg_steps))

    if not components:
        return 30.0
    return _clamp(sum(components) / len(components))


def _latest_lab_panel(ehr: list[EHRRecord]) -> dict[str, float] | None:
    """Return the payload of the most recent lab_panel record, or None."""
    panels = [r for r in ehr if r.record_type == "lab_panel"]
    if not panels:
        return None
    panels.sort(key=lambda r: r.recorded_at, reverse=True)
    payload: dict[str, float] = {
        k: float(v) for k, v in panels[0].payload.items() if v is not None
    }
    return payload


def _metabolic_subscore(lab: dict[str, float] | None) -> float:
    """Metabolic sub-score (0–100).

    Algorithm (docs/10-vitality-formula.md §2.3):
    Lerp hba1c, fasting_glucose, crp independently; return mean of available.
    """
    if lab is None:
        return 65.0

    components: list[float] = []

    hba1c = lab.get("hba1c_pct")
    if hba1c is not None:
        components.append(_lerp(_HBA1C_ANCHORS, hba1c))

    glucose = lab.get("fasting_glucose_mmol")
    if glucose is not None:
        components.append(_lerp(_GLUCOSE_ANCHORS, glucose))

    crp = lab.get("crp_mg_l")
    if crp is not None:
        components.append(_lerp(_CRP_ANCHORS, crp))

    if not components:
        return 65.0
    return _clamp(sum(components) / len(components))


def _cardio_subscore(lab: dict[str, float] | None, wearable: list[WearableDay]) -> float:
    """Cardiovascular sub-score (0–100).

    Algorithm (docs/10-vitality-formula.md §2.4):
    Lerp sbp, ldl, and 7-day mean resting HR independently; return mean of available.
    """
    components: list[float] = []

    if lab is not None:
        sbp = lab.get("sbp_mmhg")
        if sbp is not None:
            components.append(_lerp(_SBP_ANCHORS, sbp))

        ldl = lab.get("ldl_mmol")
        if ldl is not None:
            components.append(_lerp(_LDL_ANCHORS, ldl))

    # Resting HR: 7-day mean over the scoring window
    hr_vals = [d.resting_hr_bpm for d in wearable if d.resting_hr_bpm is not None]
    if hr_vals:
        avg_hr = sum(hr_vals) / len(hr_vals)
        components.append(_lerp(_RESTING_HR_ANCHORS, avg_hr))

    if not components:
        return 65.0
    return _clamp(sum(components) / len(components))


def _lifestyle_subscore(lifestyle: LifestyleProfile | None) -> float:
    """Lifestyle & Behavioural sub-score (0–100).

    Algorithm (docs/10-vitality-formula.md §2.5):
    - diet_quality_score × 10
    - exercise_sessions_weekly via lerp
    - stress_level (inverted) via lerp
    - sleep_satisfaction × 10
    Returns mean of available signals; fallback 60 if none.
    """
    if lifestyle is None:
        return 60.0

    components: list[float] = []

    if lifestyle.diet_quality_score is not None:
        components.append(_clamp(float(lifestyle.diet_quality_score) * 10.0))

    if lifestyle.exercise_sessions_weekly is not None:
        components.append(_lerp(_EXERCISE_ANCHORS, float(lifestyle.exercise_sessions_weekly)))

    if lifestyle.stress_level is not None:
        components.append(_lerp(_STRESS_ANCHORS, float(lifestyle.stress_level)))

    if lifestyle.sleep_satisfaction is not None:
        components.append(_clamp(float(lifestyle.sleep_satisfaction) * 10.0))

    if not components:
        return 60.0
    return _clamp(sum(components) / len(components))


# ---------------------------------------------------------------------------
# Risk-flag derivation (thresholds unchanged from v1)
# ---------------------------------------------------------------------------


def _derive_risk_flags(
    lab: dict[str, float] | None,
    wearable: list[WearableDay],
) -> list[str]:
    """Derive short risk-flag codes from available data.

    Thresholds are intentionally conservative (wellness framing, not clinical).

    Flag codes:
        lipid_ldl_elevated         — LDL >= 3.0 mmol/L
        lipid_cholesterol_elevated — total cholesterol >= 6.5 mmol/L
        bp_borderline_elevated     — SBP 120–139 mmHg
        metabolic_hba1c_elevated   — HbA1c >= 5.7 %
        sleep_duration_low         — mean sleep_duration_hrs < 6.5 h over window
        activity_low               — total active_minutes over window < 100 min
    """
    flags: list[str] = []

    if lab is not None:
        ldl = lab.get("ldl_mmol")
        if ldl is not None and ldl >= 3.0:
            flags.append("lipid_ldl_elevated")

        chol = lab.get("total_cholesterol_mmol")
        if chol is not None and chol >= 6.5:
            flags.append("lipid_cholesterol_elevated")

        sbp = lab.get("sbp_mmhg")
        if sbp is not None and 120.0 <= sbp < 140.0:
            flags.append("bp_borderline_elevated")

        hba1c = lab.get("hba1c_pct")
        if hba1c is not None and hba1c >= 5.7:
            flags.append("metabolic_hba1c_elevated")

    if wearable:
        sleep_hrs = [d.sleep_duration_hrs for d in wearable if d.sleep_duration_hrs is not None]
        if sleep_hrs and (sum(sleep_hrs) / len(sleep_hrs)) < 6.5:
            flags.append("sleep_duration_low")

        active_mins = [d.active_minutes for d in wearable if d.active_minutes is not None]
        if active_mins and sum(active_mins) < 100:
            flags.append("activity_low")

    return flags


# ---------------------------------------------------------------------------
# Per-day trend score (sleep + activity only — wearable-only by design)
# ---------------------------------------------------------------------------


def _day_score(day: WearableDay) -> float:
    """Simplified per-day score using only sleep and activity signals.

    Used for the sparkline trend (see docs/10-vitality-formula.md §4).
    Lab data is intentionally excluded so the trend reflects wearable progress,
    not the (infrequent) lab update cadence.
    """
    sleep_s = _sleep_subscore([day])
    activity_s = _activity_subscore([day])
    return _clamp((sleep_s + activity_s) / 2.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_vitality(
    patient: Patient,
    ehr: list[EHRRecord],
    wearable: list[WearableDay],
    lifestyle: LifestyleProfile | None,
) -> VitalityResult:
    """Compute a heuristic VitalityResult from available patient data.

    Parameters
    ----------
    patient:
        The patient identity record (used for context; not mutated).
    ehr:
        Full list of EHRRecord rows for this patient.  The function extracts
        the most recent ``lab_panel`` record automatically.
    wearable:
        All available WearableDay rows, any ordering.  The function sorts
        internally; uses the most-recent ``SCORING_WINDOW_DAYS`` days for
        sub-scores and ``TREND_WINDOW_DAYS`` days for the trend sparkline.
    lifestyle:
        The patient's LifestyleProfile, or None if no survey has been
        submitted yet.

    Returns
    -------
    VitalityResult
        score, subscores, risk_flags, trend, disclaimer — all wellness-framed.
        The ``disclaimer`` field is always equal to the module-level
        ``DISCLAIMER`` constant.  The ``trend`` array is sorted newest-first
        and contains at most ``TREND_WINDOW_DAYS`` points.
    """
    # Sort wearable newest-first
    sorted_wearable = sorted(wearable, key=lambda d: d.date, reverse=True)

    # Scoring window: last 7 days for sub-score computation
    scoring_window = sorted_wearable[:SCORING_WINDOW_DAYS]

    # Trend window: last 30 days for sparkline
    trend_window = sorted_wearable[:TREND_WINDOW_DAYS]

    # Extract latest lab panel payload
    lab = _latest_lab_panel(ehr)

    # Compute sub-scores using the scoring window
    subscores: dict[str, float] = {
        "sleep": _sleep_subscore(scoring_window),
        "activity": _activity_subscore(scoring_window),
        "metabolic": _metabolic_subscore(lab),
        "cardio": _cardio_subscore(lab, scoring_window),
        "lifestyle": _lifestyle_subscore(lifestyle),
    }

    # Weighted composite — clamped as a safety net
    score = _clamp(
        sum(_WEIGHTS[k] * v for k, v in subscores.items())
    )

    # Risk flags
    risk_flags = _derive_risk_flags(lab, scoring_window)

    # Trend: per-day sleep+activity blend over the trend window, newest-first
    trend = [TrendPoint(date=day.date, score=_day_score(day)) for day in trend_window]

    return VitalityResult(
        score=score,
        subscores=subscores,
        risk_flags=risk_flags,
        trend=trend,
        disclaimer=DISCLAIMER,
    )
