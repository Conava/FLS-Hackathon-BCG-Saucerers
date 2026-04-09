"""Unit tests for CSVDataSource adapter.

TDD cycle: all tests were written before the implementation. Run them against
the fixtures in tests/fixtures/ which contain 10 patients including PT0282.

Fixture patients: PT0001–PT0009 plus PT0282.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from app.adapters import get_source
from app.adapters.base import PatientData

# Absolute path to the fixture directory, resolved from this file's location.
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect(data_dir: Path) -> list[PatientData]:
    """Drain the async generator from CSVDataSource into a list."""
    source = get_source("csv", data_dir=data_dir)
    results: list[PatientData] = []
    async for pd in source.iter_patients():
        results.append(pd)
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_csv_source_registered() -> None:
    """get_source('csv', ...) must return a CSVDataSource without raising."""
    from app.adapters.csv_source import CSVDataSource  # import after registering

    source = get_source("csv", data_dir=FIXTURES_DIR)
    assert isinstance(source, CSVDataSource)


@pytest.mark.asyncio
async def test_csv_source_yields_expected_patient_count() -> None:
    """10 patients in the fixture → 10 PatientData objects yielded."""
    patients = await _collect(FIXTURES_DIR)
    assert len(patients) == 10


@pytest.mark.asyncio
async def test_csv_source_explodes_conditions_into_records() -> None:
    """A patient with N chronic conditions must produce N EHRRecord(record_type='condition')."""
    patients = await _collect(FIXTURES_DIR)
    # PT0001 has: type2_diabetes|dyslipidaemia — 2 conditions
    pt0001 = next(p for p in patients if p.patient.patient_id == "PT0001")
    conditions = [r for r in pt0001.ehr_records if r.record_type == "condition"]
    assert len(conditions) == 2
    condition_names = {r.payload["name"] for r in conditions}
    assert "type2_diabetes" in condition_names
    assert "dyslipidaemia" in condition_names
    # ICD codes must be zipped in
    icd_codes = {r.payload["icd_code"] for r in conditions}
    assert "E11" in icd_codes
    assert "E78.5" in icd_codes


@pytest.mark.asyncio
async def test_csv_source_explodes_medications_and_visits() -> None:
    """Medications and visit_history entries must each expand into EHRRecord rows."""
    patients = await _collect(FIXTURES_DIR)
    # PT0001: Metformin 500mg bd|Atorvastatin 40mg od → 2 medication records
    pt0001 = next(p for p in patients if p.patient.patient_id == "PT0001")
    meds = [r for r in pt0001.ehr_records if r.record_type == "medication"]
    assert len(meds) == 2
    raw_values = {r.payload["raw"] for r in meds}
    assert "Metformin 500mg bd" in raw_values
    assert "Atorvastatin 40mg od" in raw_values

    # PT0001 visit_history: 4 visits
    visits = [r for r in pt0001.ehr_records if r.record_type == "visit"]
    assert len(visits) == 4
    # Check one parsed visit date
    visit_dates = {r.recorded_at.date().isoformat() for r in visits}
    assert "2022-04-15" in visit_dates
    # Visit payload must carry icd_code
    visit_payloads = [r.payload for r in visits if r.recorded_at.date().isoformat() == "2022-04-15"]
    assert visit_payloads[0]["icd_code"] == "E11"


@pytest.mark.asyncio
async def test_csv_source_single_lab_panel_per_patient() -> None:
    """Every patient must have exactly one EHRRecord(record_type='lab_panel')
    and the payload must contain total_cholesterol_mmol."""
    patients = await _collect(FIXTURES_DIR)
    for pd in patients:
        panels = [r for r in pd.ehr_records if r.record_type == "lab_panel"]
        assert len(panels) == 1, (
            f"{pd.patient.patient_id} has {len(panels)} lab_panel records"
        )
        assert "total_cholesterol_mmol" in panels[0].payload, (
            f"{pd.patient.patient_id} lab_panel missing total_cholesterol_mmol"
        )


@pytest.mark.asyncio
async def test_csv_source_pt0282_name_anna_weber() -> None:
    """PT0282 must have name='Anna Weber'."""
    patients = await _collect(FIXTURES_DIR)
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    assert anna.patient.name == "Anna Weber"


@pytest.mark.asyncio
async def test_csv_source_pt0282_lab_values_exact() -> None:
    """PT0282 lab panel must match the pitch data exactly.

    From docs/02-persona-and-journey.md:
        total_cholesterol = 7.05, ldl = 3.84, sbp = 128
    """
    patients = await _collect(FIXTURES_DIR)
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    panel = next(r for r in anna.ehr_records if r.record_type == "lab_panel")
    assert panel.payload["total_cholesterol_mmol"] == pytest.approx(7.05)
    assert panel.payload["ldl_mmol"] == pytest.approx(3.84)
    assert panel.payload["sbp_mmhg"] == pytest.approx(128)


@pytest.mark.asyncio
async def test_csv_source_lab_panel_recorded_at_matches_latest_wearable_date() -> None:
    """lab_panel recorded_at must equal the latest wearable date for that patient.

    PT0282's last wearable row is 2023-12-31, so recorded_at.date() == 2023-12-31.
    """
    patients = await _collect(FIXTURES_DIR)
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    panel = next(r for r in anna.ehr_records if r.record_type == "lab_panel")
    # Latest wearable date from fixture
    latest_wearable = max(w.date for w in anna.wearable_days)
    assert panel.recorded_at.date() == latest_wearable


@pytest.mark.asyncio
async def test_csv_source_lifestyle_parsed() -> None:
    """LifestyleProfile must be populated with fields from lifestyle_survey.csv."""
    patients = await _collect(FIXTURES_DIR)
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    assert anna.lifestyle is not None
    assert anna.lifestyle.patient_id == "PT0282"
    assert anna.lifestyle.survey_date == datetime.date(2023, 11, 12)
    # Check a few spot values from the fixture
    assert anna.lifestyle.smoking_status == "ex"
    assert anna.lifestyle.stress_level == 2


@pytest.mark.asyncio
async def test_csv_source_naive_datetimes() -> None:
    """Every recorded_at and lifestyle survey_date-derived datetime must be tz-naive.

    asyncpg rejects timezone-aware datetimes for TIMESTAMP WITHOUT TIME ZONE columns.
    """
    patients = await _collect(FIXTURES_DIR)
    for pd in patients:
        for record in pd.ehr_records:
            assert record.recorded_at.tzinfo is None, (
                f"{pd.patient.patient_id} EHRRecord has tz-aware recorded_at"
            )


@pytest.mark.asyncio
async def test_csv_source_deterministic_ordering() -> None:
    """Running iter_patients twice must produce the same patient order."""
    run_a = await _collect(FIXTURES_DIR)
    run_b = await _collect(FIXTURES_DIR)
    ids_a = [p.patient.patient_id for p in run_a]
    ids_b = [p.patient.patient_id for p in run_b]
    assert ids_a == ids_b
    # Must be sorted
    assert ids_a == sorted(ids_a)


@pytest.mark.asyncio
async def test_csv_source_missing_wearable_fallback() -> None:
    """A patient with no wearable rows must get the fallback recorded_at
    (datetime(2025, 11, 1, 0, 0, 0)) and 0 WearableDays.

    We use a data_dir that has EHR + lifestyle but no wearable rows for a
    patient — we accomplish this via an in-memory fixture approach using a
    tmp_path-based fixture dir.
    """
    import csv
    import shutil
    import tempfile

    # Build a temp dir with only 1 patient who has no wearable rows
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # EHR: one patient "PT9999" — no chronic conditions, no meds, one visit
        ehr_header = (
            "patient_id,age,sex,country,height_cm,weight_kg,bmi,smoking_status,"
            "alcohol_units_weekly,chronic_conditions,icd_codes,n_chronic_conditions,"
            "medications,n_visits_2yr,visit_history,"
            "sbp_mmhg,dbp_mmhg,total_cholesterol_mmol,ldl_mmol,hdl_mmol,"
            "triglycerides_mmol,hba1c_pct,fasting_glucose_mmol,crp_mg_l,egfr_ml_min\n"
        )
        ehr_row = (
            "PT9999,30,M,Germany,180.0,80.0,24.7,never,0,"
            "none,Z00.0,0,None,1,2023-01-01:Z00.0,"
            "120,80,5.0,3.0,1.5,1.0,5.0,4.5,0.5,90\n"
        )
        (tmp_path / "ehr_records.csv").write_text(ehr_header + ehr_row)

        # Wearable: empty (header only)
        wearable_header = (
            "patient_id,date,resting_hr_bpm,hrv_rmssd_ms,steps,active_minutes,"
            "sleep_duration_hrs,sleep_quality_score,deep_sleep_pct,spo2_avg_pct,"
            "calories_burned_kcal\n"
        )
        (tmp_path / "wearable_telemetry_1.csv").write_text(wearable_header)

        # Lifestyle: one row
        lifestyle_header = (
            "patient_id,survey_date,smoking_status,alcohol_units_weekly,"
            "diet_quality_score,fruit_veg_servings_daily,meal_frequency_daily,"
            "exercise_sessions_weekly,sedentary_hrs_day,stress_level,sleep_satisfaction,"
            "mental_wellbeing_who5,self_rated_health,water_glasses_daily\n"
        )
        lifestyle_row = "PT9999,2023-11-01,never,0,7,3.0,3,4,6.0,3,7,20,4,8\n"
        (tmp_path / "lifestyle_survey.csv").write_text(lifestyle_header + lifestyle_row)

        source = get_source("csv", data_dir=tmp_path)
        results: list[PatientData] = []
        async for pd in source.iter_patients():
            results.append(pd)

        assert len(results) == 1
        pt = results[0]
        assert len(pt.wearable_days) == 0

        # Lab panel must use the fallback datetime
        panel = next(r for r in pt.ehr_records if r.record_type == "lab_panel")
        assert panel.recorded_at == datetime.datetime(2025, 11, 1, 0, 0, 0)
        assert panel.recorded_at.tzinfo is None


@pytest.mark.asyncio
async def test_csv_source_patient_with_none_medications() -> None:
    """A patient whose medications field is 'None' must produce 0 medication records."""
    patients = await _collect(FIXTURES_DIR)
    # PT0282 has None medications
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    meds = [r for r in anna.ehr_records if r.record_type == "medication"]
    assert len(meds) == 0


@pytest.mark.asyncio
async def test_csv_source_patient_with_no_conditions() -> None:
    """A patient with 'none' chronic_conditions must produce 0 condition records."""
    patients = await _collect(FIXTURES_DIR)
    # PT0282 has none conditions
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    conditions = [r for r in anna.ehr_records if r.record_type == "condition"]
    assert len(conditions) == 0


@pytest.mark.asyncio
async def test_csv_source_wearable_days_count() -> None:
    """PT0282 must have 90 WearableDay rows (matching the fixture)."""
    patients = await _collect(FIXTURES_DIR)
    anna = next(p for p in patients if p.patient.patient_id == "PT0282")
    assert len(anna.wearable_days) == 90
