"""
generate_rebecca_data.py — Seed Rebecca Mueller's (PT0199) positive-trajectory dataset.

What it does:
  1. Replaces PT0199's 90 wearable rows in data/wearable_telemetry_1.csv
     with 90 new rows dated 2026-01-11 through 2026-04-10 showing gentle improvement.
  2. Updates PT0199's single row in data/lifestyle_survey.csv with better lifestyle values.
  3. Updates PT0199's single row in data/ehr_records.csv with improved-but-managed T2D labs.
  4. Creates data/daily_log.csv with 90 daily self-report rows for PT0199.
  5. Creates data/meal_log.csv with 14 meal entries for PT0199 (2026-03-28 through 2026-04-10).

How to run:
  python scripts/generate_rebecca_data.py

Why the seed is fixed:
  random.seed(199) ensures every run produces byte-identical CSVs.
  This makes the script idempotent — running it twice shows no git diff.
"""

import csv
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants — tweak here without touching generation logic
# ---------------------------------------------------------------------------

PATIENT_ID = "PT0199"
SEED = 199

# Date window: 90 days ending today (2026-04-10)
START_DATE = date(2026, 1, 11)
END_DATE = date(2026, 4, 10)

# Wearable ramp: (start_value, end_value, noise_sigma)
WEARABLE_RAMPS = {
    "steps":                (3000,  9500,  800),
    "active_minutes":       (8,     35,    5),
    "sleep_duration_hrs":   (6.2,   7.6,   0.3),
    "sleep_quality_score":  (55,    85,    4),
    "deep_sleep_pct":       (13,    22,    2),
    "resting_hr_bpm":       (78,    64,    2),   # ramps DOWN
    "hrv_rmssd_ms":         (32,    55,    3),
    "spo2_avg_pct":         (97.5,  97.5,  0.6), # constant centre
    "calories_burned_kcal": (1500,  1800,  80),
}

# Lifestyle survey target values for PT0199
LIFESTYLE_UPDATE = {
    "survey_date":               "2026-04-05",
    "smoking_status":            "ex",
    "alcohol_units_weekly":      "1.0",
    "diet_quality_score":        "8",
    "fruit_veg_servings_daily":  "5.5",
    "meal_frequency_daily":      "4",
    "water_glasses_daily":       "9",
    "exercise_sessions_weekly":  "5",
    "sedentary_hrs_day":         "6",
    "stress_level":              "4",
    "sleep_satisfaction":        "8",
    "mental_wellbeing_who5":     "68",
    "self_rated_health":         "7",
}

# EHR lab updates for PT0199 (only these fields change)
EHR_UPDATE = {
    "sbp_mmhg":              "132",
    "dbp_mmhg":              "82",
    "total_cholesterol_mmol":"5.1",
    "ldl_mmol":              "2.9",
    "hdl_mmol":              "1.45",
    "triglycerides_mmol":    "1.6",
    "hba1c_pct":             "6.5",
    "fasting_glucose_mmol":  "7.4",
    "crp_mg_l":              "1.8",
}

# Daily log ramps
DAILY_RAMPS = {
    "mood":            (3, 5),
    "workout_minutes": (10, 40, 5),   # (start, end, noise_sigma)
    "water_ml":        (1200, 2200, 150),
    "sleep_quality":   (3, 5),
}

WORKOUT_TYPES = ["walk", "yoga", "bike", "strength", "walk"]

# Meal library: (description, protein_g, carbs_g, fat_g, fiber_g, calories_kcal, longevity_swap)
MEAL_LIBRARY = [
    (
        "Grilled salmon bowl with quinoa and steamed broccoli",
        35, 42, 14, 9, 430,
        "Swap white rice for quinoa to flatten glucose response",
    ),
    (
        "Lentil and vegetable soup with whole-grain sourdough",
        28, 52, 10, 14, 410,
        "Lentils instead of pasta — +12g fiber per serving",
    ),
    (
        "Greek yogurt with walnuts, blueberries and chia seeds",
        25, 32, 16, 8, 365,
        "Full-fat yogurt and nuts slow down carb absorption",
    ),
    (
        "Chicken, chickpea and spinach curry",
        38, 38, 12, 11, 415,
        "Chickpeas deliver resistant starch and plant protein",
    ),
    (
        "Pan-seared mackerel with roasted sweet potato and kale",
        32, 40, 15, 10, 420,
        "Omega-3s from mackerel improve insulin sensitivity",
    ),
    (
        "Tempeh stir-fry with bok choy and brown rice",
        30, 48, 11, 9, 405,
        "Tempeh fermented soy has lower glycemic impact than tofu",
    ),
    (
        "Steel-cut oats with almond butter and chia",
        27, 45, 13, 12, 400,
        "Steel-cut oats release glucose slower than instant oats",
    ),
    (
        "Baked cod with roasted chickpeas and mixed salad",
        36, 35, 11, 10, 385,
        "Legumes and white fish keep post-meal glucose flat",
    ),
    (
        "Avocado and egg on rye bread with rocket",
        26, 30, 18, 8, 375,
        "Rye bread has lower GI than white wheat bread",
    ),
    (
        "Black bean and sweet potato bowl with tahini dressing",
        28, 50, 12, 13, 420,
        "Black beans raise satiety and blunt glycemic spike",
    ),
    (
        "Poached chicken with edamame, cucumber and sesame",
        40, 28, 10, 8, 360,
        "High protein, low-carb keeps HbA1c trending down",
    ),
    (
        "Spiced lentil dal with cauliflower and basmati rice",
        30, 55, 10, 15, 430,
        "Lentils add 15g fiber which slows gastric emptying",
    ),
    (
        "Sardines on rye with sliced tomato and olive oil",
        32, 25, 16, 7, 375,
        "Sardines are rich in EPA/DHA for cardiovascular benefit",
    ),
    (
        "Roasted vegetable and feta frittata with side salad",
        29, 18, 17, 6, 340,
        "Egg-based meals spike glucose less than cereal breakfasts",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"


def _ramp(start: float, end: float, i: int, n: int) -> float:
    """Linear interpolation from start to end over n steps (0-indexed)."""
    if n <= 1:
        return start
    return start + (end - start) * i / (n - 1)


def _dates(start: date, end: date) -> list[date]:
    days = (end - start).days + 1
    return [start + timedelta(days=k) for k in range(days)]


def _update_csv_rows(path: Path, predicate, transform) -> int:
    """Read CSV, apply transform to rows where predicate(row) is True, write back."""
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        rows = list(reader)
    updated = 0
    for row in rows:
        if predicate(row):
            transform(row)
            updated += 1
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return updated


# ---------------------------------------------------------------------------
# Wearable telemetry
# ---------------------------------------------------------------------------

def generate_wearable_rows(dates: list[date]) -> list[dict]:
    n = len(dates)
    rows = []
    for i, d in enumerate(dates):
        t = i / (n - 1) if n > 1 else 0.0

        def rv(start, end, sigma):
            base = start + (end - start) * t
            return base + random.gauss(0, sigma)

        steps_raw = rv(*WEARABLE_RAMPS["steps"])
        active_raw = rv(*WEARABLE_RAMPS["active_minutes"])
        sleep_raw = rv(*WEARABLE_RAMPS["sleep_duration_hrs"])
        sq_raw = rv(*WEARABLE_RAMPS["sleep_quality_score"])
        ds_raw = rv(*WEARABLE_RAMPS["deep_sleep_pct"])
        hr_raw = rv(*WEARABLE_RAMPS["resting_hr_bpm"])
        hrv_raw = rv(*WEARABLE_RAMPS["hrv_rmssd_ms"])
        spo2_raw = rv(*WEARABLE_RAMPS["spo2_avg_pct"])
        cal_raw = rv(*WEARABLE_RAMPS["calories_burned_kcal"])

        rows.append({
            "patient_id":           PATIENT_ID,
            "date":                 str(d),
            "resting_hr_bpm":       max(40, int(round(hr_raw))),
            "hrv_rmssd_ms":         round(max(0.0, hrv_raw), 1),
            "steps":                max(0, int(round(steps_raw))),
            "active_minutes":       max(0, int(round(active_raw))),
            "sleep_duration_hrs":   round(max(0.0, sleep_raw), 1),
            "sleep_quality_score":  round(max(0.0, sq_raw), 1),
            "deep_sleep_pct":       round(max(0.0, ds_raw), 1),
            "spo2_avg_pct":         round(max(90.0, min(100.0, spo2_raw)), 1),
            "calories_burned_kcal": max(0, int(round(cal_raw))),
        })
    return rows


def write_wearable(dates: list[date]) -> (list[dict], int):
    path = DATA_DIR / "wearable_telemetry_1.csv"
    new_rows = generate_wearable_rows(dates)

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        all_rows = [r for r in reader if r["patient_id"] != PATIENT_ID]

    all_rows.extend(new_rows)
    # Sort by patient_id then date to keep file deterministic
    all_rows.sort(key=lambda r: (r["patient_id"], r["date"]))

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    return new_rows, len(new_rows)


# ---------------------------------------------------------------------------
# Lifestyle survey
# ---------------------------------------------------------------------------

def write_lifestyle() -> int:
    path = DATA_DIR / "lifestyle_survey.csv"

    def is_rebecca(row):
        return row["patient_id"] == PATIENT_ID

    def update(row):
        row.update(LIFESTYLE_UPDATE)

    return _update_csv_rows(path, is_rebecca, update)


# ---------------------------------------------------------------------------
# EHR records
# ---------------------------------------------------------------------------

def write_ehr() -> int:
    path = DATA_DIR / "ehr_records.csv"

    def is_rebecca(row):
        return row["patient_id"] == PATIENT_ID

    def update(row):
        row.update(EHR_UPDATE)

    return _update_csv_rows(path, is_rebecca, update)


# ---------------------------------------------------------------------------
# Daily log
# ---------------------------------------------------------------------------

def generate_daily_log(dates: list[date], wearable_rows: list[dict]) -> list[dict]:
    n = len(dates)
    # Build a lookup: date_str -> sleep_duration_hrs from wearable
    wearable_sleep = {r["date"]: float(r["sleep_duration_hrs"]) for r in wearable_rows}

    rows = []
    for i, d in enumerate(dates):
        t = i / (n - 1) if n > 1 else 0.0

        mood_raw = 3 + (5 - 3) * t
        mood = int(round(min(5, max(1, mood_raw))))

        workout_min_raw = 10 + (40 - 10) * t + random.gauss(0, 5)
        workout_min = max(0, int(round(workout_min_raw)))

        base_sleep = wearable_sleep.get(str(d), 7.0)
        sleep_h = round(base_sleep + random.gauss(0, 0.2), 1)

        water_raw = 1200 + (2200 - 1200) * t + random.gauss(0, 150)
        water_ml = max(0, int(round(water_raw)))

        alcohol = 1.0 if i % 10 == 9 else 0.0

        sq_raw = 3 + (5 - 3) * t
        sleep_quality = int(round(min(5, max(1, sq_raw))))

        workout_type = WORKOUT_TYPES[i % 5]
        workout_intensity = "low" if i < 30 else "med"

        rows.append({
            "patient_id":        PATIENT_ID,
            "logged_at":         f"{d}T20:00:00",
            "mood":              mood,
            "workout_minutes":   workout_min,
            "sleep_hours":       sleep_h,
            "water_ml":          water_ml,
            "alcohol_units":     alcohol,
            "sleep_quality":     sleep_quality,
            "workout_type":      workout_type,
            "workout_intensity": workout_intensity,
        })
    return rows


def write_daily_log(dates: list[date], wearable_rows: list[dict]) -> int:
    path = DATA_DIR / "daily_log.csv"
    rows = generate_daily_log(dates, wearable_rows)
    fieldnames = [
        "patient_id", "logged_at", "mood", "workout_minutes",
        "sleep_hours", "water_ml", "alcohol_units", "sleep_quality",
        "workout_type", "workout_intensity",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Meal log
# ---------------------------------------------------------------------------

def generate_meal_log() -> list[dict]:
    meal_start = date(2026, 3, 28)
    meal_end = date(2026, 4, 10)
    meal_dates = _dates(meal_start, meal_end)

    rows = []
    for idx, d in enumerate(meal_dates):
        analyzed_at = f"{d}T12:30:00"
        meal = MEAL_LIBRARY[idx % len(MEAL_LIBRARY)]
        desc, protein_g, carbs_g, fat_g, fiber_g, calories_kcal, longevity_swap = meal

        # Deterministic URI from patient_id + analyzed_at (uuid5 for idempotency)
        photo_uri = f"manual://{uuid.uuid5(uuid.NAMESPACE_DNS, f'{PATIENT_ID}:{analyzed_at}')}"

        rows.append({
            "patient_id":    PATIENT_ID,
            "analyzed_at":   analyzed_at,
            "photo_uri":     photo_uri,
            "protein_g":     protein_g,
            "carbs_g":       carbs_g,
            "fat_g":         fat_g,
            "fiber_g":       fiber_g,
            "calories_kcal": calories_kcal,
            "description":   desc,
            "longevity_swap": longevity_swap,
        })
    return rows


def write_meal_log() -> int:
    path = DATA_DIR / "meal_log.csv"
    rows = generate_meal_log()
    fieldnames = [
        "patient_id", "analyzed_at", "photo_uri",
        "protein_g", "carbs_g", "fat_g", "fiber_g", "calories_kcal",
        "description", "longevity_swap",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    random.seed(SEED)

    dates = _dates(START_DATE, END_DATE)

    wearable_rows, n_wearable = write_wearable(dates)
    n_lifestyle = write_lifestyle()
    n_ehr = write_ehr()
    n_daily = write_daily_log(dates, wearable_rows)
    n_meal = write_meal_log()

    print(
        f"Wrote {n_wearable} wearable rows, {n_daily} daily_log rows, "
        f"{n_meal} meal_log rows for {PATIENT_ID} "
        f"(lifestyle: {n_lifestyle} row, ehr: {n_ehr} row updated)"
    )


if __name__ == "__main__":
    main()
