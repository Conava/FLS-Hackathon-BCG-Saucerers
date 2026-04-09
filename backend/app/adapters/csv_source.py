"""CSV data-source adapter — first concrete DataSource implementation.

Reads three CSV files from ``data_dir``:
- ``ehr_records.csv``           — one row per patient (demographics + labs)
- ``wearable_telemetry_1.csv``  — ~90 rows per patient (daily wearable data)
- ``lifestyle_survey.csv``      — one row per patient (lifestyle survey)

Each EHR row is *exploded* into multiple typed ``EHRRecord`` rows:

1. ``Patient``                   — demographics + anthropometrics
2. ``EHRRecord(condition)``      — one per ``chronic_conditions`` entry (zipped with ``icd_codes``)
3. ``EHRRecord(medication)``     — one per ``medications`` entry (``None`` row → 0 records)
4. ``EHRRecord(visit)``          — one per ``visit_history`` entry (``date:icd_code`` pairs)
5. ``EHRRecord(lab_panel)``      — one per patient; ``recorded_at`` = latest wearable date
                                    (documented proxy — the CSV has no explicit lab date)
6. ``WearableDay``               — one per wearable CSV row for that patient
7. ``LifestyleProfile``          — one per lifestyle CSV row for that patient

All datetimes produced by this adapter are **naive UTC** — ``TIMESTAMP WITHOUT
TIME ZONE`` columns in Postgres/asyncpg reject tz-aware values.

Lab panel ``recorded_at`` fallback: if a patient has no wearable data (rare in
the source CSVs, possible in tests), we use ``datetime(2025, 11, 1, 0, 0, 0)``
as a documented proxy.

Patient name mapping:
- Known demo personas → realistic names (see ``_PATIENT_NAMES``)
- all others → ``f"Patient {patient_id}"``
"""

from __future__ import annotations

import csv
import datetime
from collections import defaultdict
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from app.adapters import register
from app.adapters.base import PatientData
from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Fallback recorded_at for lab_panel when no wearable data exists.
_LAB_PANEL_FALLBACK_DT = datetime.datetime(2025, 11, 1, 0, 0, 0)

#: Named personas for demo patients (patient_id → display name).
#: PT0282 is the primary Anna Weber persona; PT0199 is the Rebecca persona
#: (see docs/02-persona-and-journey.md); PT0001–PT0005 round out the demo deck.
_PATIENT_NAMES: dict[str, str] = {
    "PT0199": "Rebecca Mueller",
    "PT0282": "Anna Weber",
    "PT0001": "Marcus Becker",
    "PT0002": "Sofia Rossi",
    "PT0003": "Jonas Lindqvist",
    "PT0004": "Aïsha Diallo",
    "PT0005": "Tomás Herrera",
}

#: Lab/BP field names to include in the lab_panel payload (order preserved for docs).
_LAB_FIELDS: tuple[str, ...] = (
    "sbp_mmhg",
    "dbp_mmhg",
    "total_cholesterol_mmol",
    "ldl_mmol",
    "hdl_mmol",
    "triglycerides_mmol",
    "hba1c_pct",
    "fasting_glucose_mmol",
    "crp_mg_l",
    "egfr_ml_min",
)

#: Sentinel for patients with no conditions/medications recorded.
_NONE_SENTINEL = "none"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _parse_float(value: str) -> float | None:
    """Parse a CSV string to float, returning None for empty/invalid values."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    """Parse a CSV string to int, returning None for empty/invalid values."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def _patient_name(patient_id: str) -> str:
    """Return the display name for a patient.

    Known demo personas (PT0199, PT0282, PT0001–PT0005) get realistic names so
    the frontend greeting shows "Good morning, Rebecca" rather than the
    placeholder "Patient PT0199".  All other patients receive a synthetic name
    based on their ID.
    """
    return _PATIENT_NAMES.get(patient_id, f"Patient {patient_id}")


# ---------------------------------------------------------------------------
# Sub-parsers — pure functions, no IO
# ---------------------------------------------------------------------------


def _build_patient(row: dict[str, str]) -> Patient:
    """Construct a ``Patient`` from an EHR CSV row."""
    patient_id = row["patient_id"]
    return Patient(
        patient_id=patient_id,
        name=_patient_name(patient_id),
        age=int(row["age"]),
        sex=row["sex"],
        country=row["country"],
        height_cm=_parse_float(row["height_cm"]),
        weight_kg=_parse_float(row["weight_kg"]),
        bmi=_parse_float(row["bmi"]),
        smoking_status=row.get("smoking_status") or None,
        alcohol_units_weekly=_parse_float(row.get("alcohol_units_weekly", "")),
    )


def _build_condition_records(
    patient_id: str,
    row: dict[str, str],
    fallback_dt: datetime.datetime,
) -> list[EHRRecord]:
    """Expand ``chronic_conditions`` + ``icd_codes`` into condition EHRRecords.

    Returns an empty list when ``chronic_conditions`` is ``"none"`` or empty.
    """
    conditions_raw = row.get("chronic_conditions", "").strip()
    icd_raw = row.get("icd_codes", "").strip()

    if not conditions_raw or conditions_raw.lower() == _NONE_SENTINEL:
        return []

    conditions = [c.strip() for c in conditions_raw.split("|") if c.strip()]
    icd_codes = [c.strip() for c in icd_raw.split("|") if c.strip()]

    records: list[EHRRecord] = []
    for i, condition_name in enumerate(conditions):
        icd_code = icd_codes[i] if i < len(icd_codes) else ""
        records.append(
            EHRRecord(
                patient_id=patient_id,
                record_type="condition",
                recorded_at=fallback_dt,
                payload={"name": condition_name, "icd_code": icd_code},
                source="csv",
            )
        )
    return records


def _build_medication_records(
    patient_id: str,
    row: dict[str, str],
    fallback_dt: datetime.datetime,
) -> list[EHRRecord]:
    """Expand ``medications`` into medication EHRRecords.

    Returns an empty list when ``medications`` is ``"None"`` or empty.
    """
    meds_raw = row.get("medications", "").strip()
    if not meds_raw or meds_raw.lower() == "none":
        return []

    medications = [m.strip() for m in meds_raw.split("|") if m.strip()]
    return [
        EHRRecord(
            patient_id=patient_id,
            record_type="medication",
            recorded_at=fallback_dt,
            payload={"raw": med},
            source="csv",
        )
        for med in medications
    ]


def _build_visit_records(
    patient_id: str,
    row: dict[str, str],
) -> list[EHRRecord]:
    """Parse ``visit_history`` into visit EHRRecords.

    Each entry has the format ``"YYYY-MM-DD:ICD_CODE"``.
    """
    history_raw = row.get("visit_history", "").strip()
    if not history_raw:
        return []

    records: list[EHRRecord] = []
    for entry in history_raw.split("|"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        date_str, icd_code = entry.split(":", 1)
        try:
            visit_date = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            continue  # skip malformed entries rather than crashing
        records.append(
            EHRRecord(
                patient_id=patient_id,
                record_type="visit",
                recorded_at=visit_date,
                payload={"icd_code": icd_code.strip()},
                source="csv",
            )
        )
    return records


def _build_lab_panel_record(
    patient_id: str,
    row: dict[str, str],
    recorded_at: datetime.datetime,
) -> EHRRecord:
    """Build the single lab_panel EHRRecord for a patient.

    ``recorded_at`` is the latest wearable date (proxy), or the fallback
    constant when no wearable data is available for this patient.
    """
    payload: dict[str, Any] = {}
    for field in _LAB_FIELDS:
        val = _parse_float(row.get(field, ""))
        if val is not None:
            payload[field] = val
    return EHRRecord(
        patient_id=patient_id,
        record_type="lab_panel",
        recorded_at=recorded_at,
        payload=payload,
        source="csv",
    )


def _build_wearable_day(patient_id: str, row: dict[str, str]) -> WearableDay:
    """Construct a ``WearableDay`` from one wearable CSV row."""
    date_val = datetime.date.fromisoformat(row["date"].strip())
    return WearableDay(
        patient_id=patient_id,
        date=date_val,
        resting_hr_bpm=_parse_int(row.get("resting_hr_bpm", "")),
        hrv_rmssd_ms=_parse_float(row.get("hrv_rmssd_ms", "")),
        steps=_parse_int(row.get("steps", "")),
        active_minutes=_parse_int(row.get("active_minutes", "")),
        sleep_duration_hrs=_parse_float(row.get("sleep_duration_hrs", "")),
        sleep_quality_score=_parse_float(row.get("sleep_quality_score", "")),
        deep_sleep_pct=_parse_float(row.get("deep_sleep_pct", "")),
        spo2_avg_pct=_parse_float(row.get("spo2_avg_pct", "")),
        calories_burned_kcal=_parse_int(row.get("calories_burned_kcal", "")),
    )


def _build_lifestyle_profile(row: dict[str, str]) -> LifestyleProfile:
    """Construct a ``LifestyleProfile`` from one lifestyle CSV row."""
    patient_id = row["patient_id"]
    survey_date = datetime.date.fromisoformat(row["survey_date"].strip())
    return LifestyleProfile(
        patient_id=patient_id,
        survey_date=survey_date,
        smoking_status=row.get("smoking_status") or None,
        alcohol_units_weekly=_parse_float(row.get("alcohol_units_weekly", "")),
        diet_quality_score=_parse_int(row.get("diet_quality_score", "")),
        fruit_veg_servings_daily=_parse_float(row.get("fruit_veg_servings_daily", "")),
        meal_frequency_daily=_parse_int(row.get("meal_frequency_daily", "")),
        water_glasses_daily=_parse_int(row.get("water_glasses_daily", "")),
        exercise_sessions_weekly=_parse_int(row.get("exercise_sessions_weekly", "")),
        sedentary_hrs_day=_parse_float(row.get("sedentary_hrs_day", "")),
        stress_level=_parse_int(row.get("stress_level", "")),
        sleep_satisfaction=_parse_int(row.get("sleep_satisfaction", "")),
        mental_wellbeing_who5=_parse_int(row.get("mental_wellbeing_who5", "")),
        self_rated_health=_parse_int(row.get("self_rated_health", "")),
    )


# ---------------------------------------------------------------------------
# CSV loading helpers
# ---------------------------------------------------------------------------


def _load_wearable_index(
    wearable_path: Path,
) -> dict[str, list[WearableDay]]:
    """Load the wearable CSV and return a dict keyed by patient_id.

    Returns a ``defaultdict`` so missing keys silently return ``[]``.
    """
    index: dict[str, list[WearableDay]] = defaultdict(list)
    if not wearable_path.exists():
        return index
    with wearable_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            patient_id = row["patient_id"]
            index[patient_id].append(_build_wearable_day(patient_id, row))
    return index


def _load_lifestyle_index(
    lifestyle_path: Path,
) -> dict[str, LifestyleProfile]:
    """Load the lifestyle CSV and return a dict keyed by patient_id."""
    index: dict[str, LifestyleProfile] = {}
    if not lifestyle_path.exists():
        return index
    with lifestyle_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            profile = _build_lifestyle_profile(row)
            index[profile.patient_id] = profile
    return index


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@register("csv")  # type: ignore[arg-type]  # structural Protocol — mypy can't verify at decoration site
class CSVDataSource:
    """DataSource adapter that reads the three provided CSV datasets.

    Streaming generator: yields one ``PatientData`` bundle per patient,
    building the full exploded record set in memory for that patient only,
    then releasing it before moving to the next.  The wearable and lifestyle
    indexes are pre-loaded into memory once (they are small — ~90 rows × 1,000
    patients ≈ 90,000 rows) to avoid O(N²) scans through the wearable CSV.

    Registration: ``@register("csv")`` makes this class discoverable via
    ``get_source("csv", data_dir=...)``.
    """

    name: str = "csv"

    def __init__(self, data_dir: Path = Path("data")) -> None:
        """Initialise the adapter.

        Parameters
        ----------
        data_dir:
            Directory containing ``ehr_records.csv``,
            ``wearable_telemetry_1.csv``, and ``lifestyle_survey.csv``.
            Defaults to ``data/`` relative to the working directory.
        """
        self._data_dir = Path(data_dir)

    async def iter_patients(self) -> AsyncIterator[PatientData]:
        """Yield one PatientData bundle per patient in sorted patient_id order.

        Memory note: the EHR CSV is fully materialised for sorting (so patient
        bundles are emitted in deterministic patient_id order).  The wearable
        and lifestyle side tables are pre-indexed on startup via
        ``_load_wearable_index`` / ``_load_lifestyle_index``.  Only one
        patient's exploded records are held in memory at any time during the
        yield loop.

        Yields
        ------
        PatientData
            Fully exploded bundle for one patient.
        """
        ehr_path = self._data_dir / "ehr_records.csv"
        wearable_path = self._data_dir / "wearable_telemetry_1.csv"
        lifestyle_path = self._data_dir / "lifestyle_survey.csv"

        # Pre-load side tables into indexes (O(1) lookup per patient).
        wearable_index = _load_wearable_index(wearable_path)
        lifestyle_index = _load_lifestyle_index(lifestyle_path)

        # Read EHR rows and sort by patient_id for deterministic ordering.
        ehr_rows: list[dict[str, str]] = []
        with ehr_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            ehr_rows = list(reader)
        ehr_rows.sort(key=lambda r: r["patient_id"])

        for row in ehr_rows:
            patient_id = row["patient_id"]

            # --- Wearable data for this patient ---
            wearable_days = wearable_index.get(patient_id, [])

            # --- lab_panel recorded_at proxy ---
            if wearable_days:
                latest_wearable_date = max(w.date for w in wearable_days)
                lab_panel_dt = datetime.datetime(
                    latest_wearable_date.year,
                    latest_wearable_date.month,
                    latest_wearable_date.day,
                    0,
                    0,
                    0,
                )
            else:
                lab_panel_dt = _LAB_PANEL_FALLBACK_DT

            # --- Fallback datetime for conditions / medications ---
            # Use the earliest visit_history date if available; otherwise
            # Jan 1 of two years before the lab_panel_dt year.
            visit_records = _build_visit_records(patient_id, row)
            if visit_records:
                fallback_dt = min(r.recorded_at for r in visit_records)
            else:
                fallback_dt = datetime.datetime(lab_panel_dt.year - 2, 1, 1, 0, 0, 0)

            # --- Explode EHR row into typed records ---
            ehr_records: list[EHRRecord] = []
            ehr_records.extend(_build_condition_records(patient_id, row, fallback_dt))
            ehr_records.extend(_build_medication_records(patient_id, row, fallback_dt))
            ehr_records.extend(visit_records)
            ehr_records.append(_build_lab_panel_record(patient_id, row, lab_panel_dt))

            yield PatientData(
                patient=_build_patient(row),
                ehr_records=ehr_records,
                wearable_days=wearable_days,
                lifestyle=lifestyle_index.get(patient_id),
            )


__all__ = ["CSVDataSource"]
