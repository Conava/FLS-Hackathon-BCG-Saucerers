"""Vitality Score engine — heuristic v1.

NON-CLINICAL DISCLAIMER
=======================
The weights, thresholds, and sub-score formulas below are heuristic
approximations intended for a wellness-framed product demo.  They are
*not* clinically validated, peer-reviewed, or endorsed by any medical
body.  All outputs carry the DISCLAIMER constant and must be presented
as "wellness signals, not medical advice."

Sub-score weights (composite):
  sleep      = 0.20
  activity   = 0.20
  metabolic  = 0.20
  cardio     = 0.25
  lifestyle  = 0.15

These weights were chosen to align with the BCG brief's longevity
dimensions and will be retrained on outcomes data in v2.

Wearable window ordering: ``compute_vitality`` accepts wearable days in
*any* order.  Internally they are sorted newest-first; only the last
``WEARABLE_WINDOW`` days are used.  Callers should pass the full
available history; the function caps at 7.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DISCLAIMER: str = "Wellness signal, not medical advice."

# Maximum wearable window for scoring and trend
WEARABLE_WINDOW: int = 7

# Composite weights — must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "sleep": 0.20,
    "activity": 0.20,
    "metabolic": 0.20,
    "cardio": 0.25,
    "lifestyle": 0.15,
}

# Risk-flag thresholds (non-clinical; wellness framing only)
# lipid_ldl_elevated     — LDL >= 3.0 mmol/L
# lipid_cholesterol_elevated — total cholesterol >= 6.5 mmol/L
# bp_borderline_elevated — SBP 120–139 mmHg
# sleep_duration_low     — mean sleep_duration_hrs < 6.5 h over window
# activity_low           — weekly active_minutes < 100 min
# metabolic_hba1c_elevated — HbA1c >= 5.7 %


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TrendPoint:
    """A single point on the 7-day vitality trend."""

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
# Internal scoring helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def _score_sleep_duration(hrs: float) -> float:
    """Heuristic sleep-duration score.

    7.0 h → 85; <5 h → 40; >=9 h → 70; linear between breakpoints.
    """
    if hrs >= 9.0:
        return 70.0
    if hrs >= 7.0:
        # 7–9 h: linear 85–70
        return _clamp(85.0 - (hrs - 7.0) / 2.0 * 15.0)
    if hrs >= 5.0:
        # 5–7 h: linear 40–85
        return _clamp(40.0 + (hrs - 5.0) / 2.0 * 45.0)
    return 40.0


def _sleep_subscore(wearable: list[WearableDay]) -> float:
    """Sleep & Recovery sub-score (0–100).

    Uses average sleep_quality_score when available; otherwise derives from
    sleep_duration_hrs and deep_sleep_pct.
    """
    if not wearable:
        return 50.0  # neutral fallback when no wearable data

    quality_scores: list[float] = []
    derived_scores: list[float] = []

    for day in wearable:
        if day.sleep_quality_score is not None:
            quality_scores.append(day.sleep_quality_score)
        elif day.sleep_duration_hrs is not None:
            s = _score_sleep_duration(day.sleep_duration_hrs)
            # Bonus for high deep sleep % (>25 % adds up to 10 pts)
            if day.deep_sleep_pct is not None:
                s = _clamp(s + max(0.0, (day.deep_sleep_pct - 20.0)) * 0.5)
            derived_scores.append(s)

    # Prefer the direct quality score when available
    if quality_scores:
        return _clamp(sum(quality_scores) / len(quality_scores))
    if derived_scores:
        return _clamp(sum(derived_scores) / len(derived_scores))
    return 50.0


def _activity_subscore(wearable: list[WearableDay]) -> float:
    """Activity sub-score (0–100).

    Combines:
      - Weekly active_minutes: target 150 min/week → linear 0–100, cap at 300.
      - Daily steps average: target 8,000/day → linear contribution.

    Returns the mean of whichever components are available.
    """
    if not wearable:
        return 30.0  # low-activity fallback

    n = len(wearable)

    # Active-minutes component (annualise to per-week equivalent)
    minutes_scores: list[float] = []
    minutes_vals = [d.active_minutes for d in wearable if d.active_minutes is not None]
    if minutes_vals:
        total_mins = sum(minutes_vals)
        # Scale to 7-day equivalent
        weekly_mins = total_mins * (7 / n)
        # 0 min → 0, 150 min → 100, 300+ min → 100 (capped)
        minutes_scores.append(_clamp(weekly_mins / 150.0 * 100.0))

    # Steps component
    steps_scores: list[float] = []
    steps_vals = [d.steps for d in wearable if d.steps is not None]
    if steps_vals:
        avg_steps = sum(steps_vals) / len(steps_vals)
        # 0 → 0, 8000 → 100, linear
        steps_scores.append(_clamp(avg_steps / 8000.0 * 100.0))

    components = minutes_scores + steps_scores
    if not components:
        return 30.0
    return _clamp(sum(components) / len(components))


def _latest_lab_panel(ehr: list[EHRRecord]) -> dict[str, float] | None:
    """Return the payload of the most recent lab_panel record, or None."""
    panels = [r for r in ehr if r.record_type == "lab_panel"]
    if not panels:
        return None
    # Sort by recorded_at descending; take the first
    panels.sort(key=lambda r: r.recorded_at, reverse=True)
    payload: dict[str, float] = {
        k: float(v) for k, v in panels[0].payload.items() if v is not None
    }
    return payload


def _metabolic_subscore(lab: dict[str, float] | None) -> float:
    """Metabolic sub-score (0–100).

    HbA1c: <5.7 → 100, 5.7–6.4 → 60, >6.4 → 30.
    Fasting glucose: <5.6 → 100, 5.6–6.9 → 70, else 40.
    Returns mean of available signals (neutral 65 if nothing available).
    """
    if lab is None:
        return 65.0

    components: list[float] = []

    hba1c = lab.get("hba1c_pct")
    if hba1c is not None:
        if hba1c < 5.7:
            components.append(100.0)
        elif hba1c <= 6.4:
            components.append(60.0)
        else:
            components.append(30.0)

    glucose = lab.get("fasting_glucose_mmol")
    if glucose is not None:
        if glucose < 5.6:
            components.append(100.0)
        elif glucose <= 6.9:
            components.append(70.0)
        else:
            components.append(40.0)

    if not components:
        return 65.0
    return _clamp(sum(components) / len(components))


def _cardio_subscore(lab: dict[str, float] | None, wearable: list[WearableDay]) -> float:
    """Cardiovascular sub-score (0–100).

    LDL:
      <2.6 → 95, 2.6–3.3 → 75, 3.3–4.1 → 55, >4.1 → 35.
    SBP:
      <120 → 95, 120–129 → 80, 130–139 → 60, ≥140 → 40.
    Resting HR (average from wearable):
      <60 → 95, 60–70 → 85, 70–80 → 70, >80 → 50.
    """
    components: list[float] = []

    if lab is not None:
        ldl = lab.get("ldl_mmol")
        if ldl is not None:
            if ldl < 2.6:
                components.append(95.0)
            elif ldl <= 3.3:
                components.append(75.0)
            elif ldl <= 4.1:
                components.append(55.0)
            else:
                components.append(35.0)

        sbp = lab.get("sbp_mmhg")
        if sbp is not None:
            if sbp < 120.0:
                components.append(95.0)
            elif sbp < 130.0:
                components.append(80.0)
            elif sbp < 140.0:
                components.append(60.0)
            else:
                components.append(40.0)

    # Resting HR from wearable
    hr_vals = [d.resting_hr_bpm for d in wearable if d.resting_hr_bpm is not None]
    if hr_vals:
        avg_hr = sum(hr_vals) / len(hr_vals)
        if avg_hr < 60.0:
            components.append(95.0)
        elif avg_hr <= 70.0:
            components.append(85.0)
        elif avg_hr <= 80.0:
            components.append(70.0)
        else:
            components.append(50.0)

    if not components:
        return 65.0
    return _clamp(sum(components) / len(components))


def _lifestyle_subscore(lifestyle: LifestyleProfile | None) -> float:
    """Lifestyle & Behavioural sub-score (0–100).

    diet_quality_score (1–10) → *10.
    exercise_sessions_weekly: 3+ → 85, 1–2 → 60, 0 → 30.
    stress_level (1–10) inverted: 1 → 100, 10 → 10.

    Returns mean of available signals (neutral 60 if nothing available).
    """
    if lifestyle is None:
        return 60.0

    components: list[float] = []

    if lifestyle.diet_quality_score is not None:
        components.append(_clamp(float(lifestyle.diet_quality_score) * 10.0))

    if lifestyle.exercise_sessions_weekly is not None:
        ex = lifestyle.exercise_sessions_weekly
        if ex >= 3:
            components.append(85.0)
        elif ex >= 1:
            components.append(60.0)
        else:
            components.append(30.0)

    if lifestyle.stress_level is not None:
        # Invert 1–10 scale to a wellness score
        # 1 → 100, 10 → 10; linear
        stress_score = _clamp(100.0 - (lifestyle.stress_level - 1) * (90.0 / 9.0))
        components.append(stress_score)

    if not components:
        return 60.0
    return _clamp(sum(components) / len(components))


# ---------------------------------------------------------------------------
# Risk-flag derivation
# ---------------------------------------------------------------------------


def _derive_risk_flags(
    lab: dict[str, float] | None,
    wearable: list[WearableDay],
    n_days: int,
) -> list[str]:
    """Derive short risk-flag codes from available data.

    Thresholds are intentionally conservative (wellness framing, not clinical).
    """
    flags: list[str] = []

    if lab is not None:
        ldl = lab.get("ldl_mmol")
        # lipid_ldl_elevated: LDL >= 3.0 mmol/L
        if ldl is not None and ldl >= 3.0:
            flags.append("lipid_ldl_elevated")

        chol = lab.get("total_cholesterol_mmol")
        # lipid_cholesterol_elevated: total cholesterol >= 6.5 mmol/L
        if chol is not None and chol >= 6.5:
            flags.append("lipid_cholesterol_elevated")

        sbp = lab.get("sbp_mmhg")
        # bp_borderline_elevated: SBP 120–139 mmHg
        if sbp is not None and 120.0 <= sbp < 140.0:
            flags.append("bp_borderline_elevated")

        hba1c = lab.get("hba1c_pct")
        # metabolic_hba1c_elevated: HbA1c >= 5.7 %
        if hba1c is not None and hba1c >= 5.7:
            flags.append("metabolic_hba1c_elevated")

    if wearable:
        sleep_hrs = [d.sleep_duration_hrs for d in wearable if d.sleep_duration_hrs is not None]
        # sleep_duration_low: mean sleep < 6.5 h over window
        if sleep_hrs and (sum(sleep_hrs) / len(sleep_hrs)) < 6.5:
            flags.append("sleep_duration_low")

        # activity_low: total active_minutes over window < 100 min (≈14 min/day)
        active_mins = [d.active_minutes for d in wearable if d.active_minutes is not None]
        if active_mins and sum(active_mins) < 100:
            flags.append("activity_low")

    return flags


# ---------------------------------------------------------------------------
# Per-day trend score (sleep + activity only — by design)
# ---------------------------------------------------------------------------


def _day_score(day: WearableDay) -> float:
    """Simplified per-day score using only sleep and activity signals."""
    sleep_s = _sleep_subscore([day])
    activity_s = _activity_subscore([day])
    # Equal-weight blend for trend
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
        internally and uses the most-recent ``WEARABLE_WINDOW`` days.
    lifestyle:
        The patient's LifestyleProfile, or None if no survey has been
        submitted yet.

    Returns
    -------
    VitalityResult
        score, subscores, risk_flags, trend, disclaimer — all wellness-framed.
        The ``disclaimer`` field is always equal to the module-level
        ``DISCLAIMER`` constant.
    """
    # Sort wearable newest-first and cap to window
    sorted_wearable = sorted(wearable, key=lambda d: d.date, reverse=True)
    window = sorted_wearable[:WEARABLE_WINDOW]

    # Extract latest lab panel payload
    lab = _latest_lab_panel(ehr)

    # Compute sub-scores
    subscores: dict[str, float] = {
        "sleep": _sleep_subscore(window),
        "activity": _activity_subscore(window),
        "metabolic": _metabolic_subscore(lab),
        "cardio": _cardio_subscore(lab, window),
        "lifestyle": _lifestyle_subscore(lifestyle),
    }

    # Weighted composite
    score = _clamp(
        sum(_WEIGHTS[k] * v for k, v in subscores.items())
    )

    # Risk flags
    risk_flags = _derive_risk_flags(lab, window, len(window))

    # 7-day trend (sleep + activity only, per spec)
    trend = [TrendPoint(date=day.date, score=_day_score(day)) for day in window]

    return VitalityResult(
        score=score,
        subscores=subscores,
        risk_flags=risk_flags,
        trend=trend,
        disclaimer=DISCLAIMER,
    )
