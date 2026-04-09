"""Insights service — translates VitalityResult risk flags into human-readable signals.

WELLNESS-FRAMING REQUIREMENT (HARD — MDR / legal)
==================================================
All output strings (message, signals, prevention_signals) must use
wellness language only.  The following verbs are FORBIDDEN:
  diagnose / diagnosis / treat / cure / disease

Approved vocabulary: signal, flag, elevated, consider, discuss with your
clinic, prevention panel, may benefit from, pattern worth attention,
cardiovascular markers, metabolic health.

Severity mapping (heuristic):
  high     — multiple cardio flags or HbA1c clearly elevated (≥ 6.5)
  moderate — single elevated lipid, borderline BP, or HbA1c 5.7–6.4
  low      — activity or sleep signals only
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.models import EHRRecord, LifestyleProfile
from app.services.vitality_engine import DISCLAIMER, VitalityResult

# Convenience type alias — mirrors the Insight.severity field
Severity = Literal["low", "moderate", "high"]


@dataclass
class Insight:
    """A single human-readable wellness signal derived from a risk flag.

    kind:
        Dimension the signal belongs to: "cardiovascular", "metabolic",
        "sleep", "activity", "lifestyle".
    severity:
        "low" | "moderate" | "high" — non-clinical wellness framing.
    message:
        Plain-language summary, wellness-framed.  Never contains diagnostic
        verbs (diagnose/treat/cure/disease).
    signals:
        Specific numeric observations, e.g. ["LDL 3.84 mmol/L"].
    prevention_signals:
        Suggested wellness actions, e.g.
        ["Discuss a lipid prevention panel with your clinic"].
    disclaimer:
        Always DISCLAIMER — included so every Insight carries disclosure.
    """

    kind: str
    severity: Severity
    message: str
    signals: list[str]
    prevention_signals: list[str]
    disclaimer: str = field(default=DISCLAIMER)


# ---------------------------------------------------------------------------
# Internal helpers — extract numeric values from the latest lab panel
# ---------------------------------------------------------------------------


def _latest_lab_payload(ehr: list[EHRRecord]) -> dict[str, float]:
    """Return the payload of the most recent lab_panel EHR record, or {}."""
    panels = [r for r in ehr if r.record_type == "lab_panel"]
    if not panels:
        return {}
    panels.sort(key=lambda r: r.recorded_at, reverse=True)
    return {k: float(v) for k, v in panels[0].payload.items() if v is not None}


# ---------------------------------------------------------------------------
# Flag → Insight mapping functions
# ---------------------------------------------------------------------------


def _cardiovascular_insight(
    flags: set[str],
    lab: dict[str, float],
) -> Insight | None:
    """Build a cardiovascular Insight when any cardio flag is present."""
    cardio_flags = {
        "lipid_ldl_elevated",
        "lipid_cholesterol_elevated",
        "bp_borderline_elevated",
    }
    active = cardio_flags & flags
    if not active:
        return None

    signals: list[str] = []
    prevention: list[str] = []

    ldl = lab.get("ldl_mmol")
    if "lipid_ldl_elevated" in active and ldl is not None:
        signals.append(f"LDL {ldl:.2f} mmol/L — elevated above the 3.0 mmol/L wellness threshold")
        prevention.append("Discuss a lipid prevention panel with your clinic")

    chol = lab.get("total_cholesterol_mmol")
    if "lipid_cholesterol_elevated" in active and chol is not None:
        signals.append(
            f"Total cholesterol {chol:.2f} mmol/L — a pattern worth discussing with your care team"
        )
        if "Discuss a lipid prevention panel with your clinic" not in prevention:
            prevention.append("Discuss a lipid prevention panel with your clinic")

    sbp = lab.get("sbp_mmhg")
    if "bp_borderline_elevated" in active and sbp is not None:
        signals.append(f"Systolic blood pressure {sbp:.0f} mmHg — borderline elevated range")
        prevention.append("Consider monitoring your blood pressure regularly")
        prevention.append("Review sodium intake and relaxation habits")

    # Severity: high if both lipid flags present; moderate for single flag
    if len(active) >= 2:
        severity: Severity = "high"
    else:
        severity = "moderate"

    message = (
        "Your cardiovascular markers show a pattern worth attention. "
        "Elevated lipid signals and borderline blood pressure are wellness signals "
        "that may benefit from a prevention-focused conversation with your care team."
    )

    return Insight(
        kind="cardiovascular",
        severity=severity,
        message=message,
        signals=signals,
        prevention_signals=prevention,
    )


def _metabolic_insight(
    flags: set[str],
    lab: dict[str, float],
) -> Insight | None:
    """Build a metabolic Insight when HbA1c flag is present."""
    if "metabolic_hba1c_elevated" not in flags:
        return None

    signals: list[str] = []
    prevention: list[str] = ["Consider reviewing carbohydrate quality with a nutrition specialist"]
    prevention.append("A fasting metabolic panel with your clinic can provide further context")

    hba1c = lab.get("hba1c_pct")
    if hba1c is not None:
        signals.append(f"HbA1c {hba1c:.1f}% — elevated above the 5.7% wellness threshold")

    glucose = lab.get("fasting_glucose_mmol")
    if glucose is not None and glucose >= 5.6:
        signals.append(f"Fasting glucose {glucose:.1f} mmol/L — in the borderline elevated range")

    # Severity depends on how far above the threshold
    severity: Severity = "high" if (hba1c is not None and hba1c >= 6.5) else "moderate"

    return Insight(
        kind="metabolic",
        severity=severity,
        message=(
            "Your metabolic markers show a signal worth attention. "
            "Elevated blood sugar indicators are wellness signals that may benefit from "
            "a prevention-focused check-in with your care team."
        ),
        signals=signals,
        prevention_signals=prevention,
    )


def _sleep_insight(flags: set[str]) -> Insight | None:
    """Build a sleep Insight when sleep_duration_low flag is present."""
    if "sleep_duration_low" not in flags:
        return None

    return Insight(
        kind="sleep",
        severity="low",
        message=(
            "Your recent sleep pattern shows consistently shorter nights. "
            "Sleep duration is an important wellness signal linked to recovery and energy levels."
        ),
        signals=["Average sleep duration below 6.5 hours over the recent window"],
        prevention_signals=[
            "Consider a consistent sleep and wake schedule",
            "Limit screens for 30 minutes before bed",
            "Your clinic's lifestyle team can offer personalised sleep hygiene guidance",
        ],
    )


def _activity_insight(flags: set[str]) -> Insight | None:
    """Build an activity Insight when activity_low flag is present."""
    if "activity_low" not in flags:
        return None

    return Insight(
        kind="activity",
        severity="low",
        message=(
            "Your recent activity level is below typical wellness recommendations. "
            "Regular movement is one of the most evidence-backed contributors to long-term vitality."
        ),
        signals=["Weekly active minutes below 100 — general wellness target is 150 min/week"],
        prevention_signals=[
            "Start with short daily walks and build up gradually",
            "Even 20 minutes of moderate activity per day may benefit your overall wellness",
        ],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def derive_insights(
    vitality: VitalityResult,
    ehr: list[EHRRecord],
    lifestyle: LifestyleProfile | None,
) -> list[Insight]:
    """Derive a list of wellness-framed Insights from a VitalityResult.

    Parameters
    ----------
    vitality:
        The computed VitalityResult, including risk_flags.
    ehr:
        EHR records for the patient (used to extract numeric values for
        the ``signals`` field — e.g. "LDL 3.84 mmol/L").
    lifestyle:
        The patient's LifestyleProfile, or None.

    Returns
    -------
    list[Insight]
        Zero or more Insights.  An empty list means no actionable signals
        were detected.  Order: cardiovascular, metabolic, sleep, activity.

    Notes
    -----
    All output strings are wellness-framed.  The forbidden verbs
    (diagnose/treat/cure/disease) must never appear in any field.
    This is a legal requirement per MDR framing rules — see
    docs/08-legal-compliance.md.
    """
    flags = set(vitality.risk_flags)
    lab = _latest_lab_payload(ehr)

    insights: list[Insight] = []

    cardio = _cardiovascular_insight(flags, lab)
    if cardio is not None:
        insights.append(cardio)

    metabolic = _metabolic_insight(flags, lab)
    if metabolic is not None:
        insights.append(metabolic)

    sleep = _sleep_insight(flags)
    if sleep is not None:
        insights.append(sleep)

    activity = _activity_insight(flags)
    if activity is not None:
        insights.append(activity)

    return insights
