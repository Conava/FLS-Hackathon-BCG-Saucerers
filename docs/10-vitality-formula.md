# Vitality Score & Outlook Formula Specification

> **Audience:** Backend engineers implementing `vitality_engine.py` and `outlook_engine.py`, and anyone who needs to explain the score on a slide.
>
> **Status:** This document is the single source of truth. When the formula and the code disagree, fix the code.
>
> **NON-CLINICAL DISCLAIMER:** All scores, projections, and thresholds in this document are heuristic wellness signals. They are not clinically validated, peer-reviewed, or endorsed by any medical body. Every output must be presented as "wellness signal, not medical advice."

---

## Table of Contents

1. [Overview](#1-overview)
2. [Subscore Specifications](#2-subscore-specifications)
   - [2.1 Sleep](#21-sleep-subscore)
   - [2.2 Activity](#22-activity-subscore)
   - [2.3 Metabolic](#23-metabolic-subscore)
   - [2.4 Cardio](#24-cardio-subscore)
   - [2.5 Lifestyle](#25-lifestyle-subscore)
3. [Composite Score](#3-composite-score)
4. [Scoring Window vs Trend Window](#4-scoring-window-vs-trend-window)
5. [Outlook Formula](#5-outlook-formula)
6. [Worked Example — Rebecca (PT0199)](#6-worked-example--rebecca-pt0199)
7. [Reasoning and Trade-offs](#7-reasoning-and-trade-offs)

---

## 1. Overview

### Vitality Score

The **Vitality Score** is a single number in [0, 100] summarising a patient's current wellness state across five dimensions: sleep, physical activity, metabolic health, cardiovascular health, and lifestyle behaviour. It is updated every time the ingest pipeline runs (or on demand) and uses data from the most recent **7-day scoring window**.

It is *not* a medical risk score. It does not diagnose, treat, cure, or prevent disease. It is a motivational wellness signal.

### Outlook Projection

The **Outlook** projects what the Vitality Score *could* reach at 3, 6, and 12 months **if the patient maintains their current protocol adherence and streak**. The projection is bounded by a ceiling of 95 (a perfect-health proxy, not a clinical target) and saturates as the gap closes — the same "closing the gap" intuition as compound interest.

The slide story in one sentence: *"Better habits close the gap to your ceiling; the longer you stick with it, the more of that gap you capture."*

---

## 2. Subscore Specifications

All five subscores use **piecewise-linear interpolation** between population-health anchors. The primitive is:

```
lerp(anchors, x):
    anchors = sorted list of (input_value, output_score) pairs
    if x <= anchors[0].input:  return anchors[0].output        # clamp low
    if x >= anchors[-1].input: return anchors[-1].output       # clamp high
    find i such that anchors[i].input <= x < anchors[i+1].input
    f = (x - anchors[i].input) / (anchors[i+1].input - anchors[i].input)
    return anchors[i].output + f * (anchors[i+1].output - anchors[i].output)
```

All subscores are clamped to [0, 100] after computation. Missing inputs are excluded from the average; if all inputs are missing, the fallback value is returned.

### 2.1 Sleep Subscore

**Inputs** (from `WearableDay` records over `SCORING_WINDOW_DAYS`):

| Field | Type | Notes |
|---|---|---|
| `sleep_duration_hrs` | float | Hours of total sleep per night |
| `sleep_quality_score` | float \| None | 0–100 quality signal from wearable; optional |
| `deep_sleep_pct` | float \| None | % of sleep spent in deep/slow-wave stage; optional |

**Algorithm:**

1. Compute `duration_score` via `lerp` on `sleep_duration_hrs` using the anchors below.
2. If `sleep_quality_score` is available, compute `quality_avg = mean(duration_score, sleep_quality_score)`. Otherwise `quality_avg = duration_score`.
3. If the 7-day mean `deep_sleep_pct ≥ 20%`, add a bonus of **+5** (deep sleep reflects restorative efficiency). Apply bonus after step 2, then clamp to [0, 100].

**Duration anchors:**

| sleep_duration_hrs | score | Rationale |
|---|---|---|
| 4 | 20 | Severe deprivation — broad consensus on cognitive and metabolic harm below 5 h |
| 6 | 55 | Below the 7 h threshold recommended by AHA/CDC; moderate impairment |
| 7.5 | 95 | Peak of the U-curve; aligns with 7–8 h consensus optimum |
| 9 | 80 | Slight descent — oversleeping correlates with comorbidities at population level |
| 10 | 55 | Extended oversleeping; same concern as 6 h but opposite cause |

**Fallback:** 50 (neutral, no data).

---

### 2.2 Activity Subscore

**Inputs** (from `WearableDay` records over `SCORING_WINDOW_DAYS`):

| Field | Type | Notes |
|---|---|---|
| `active_minutes` | int \| None | Active minutes per day (moderate-to-vigorous intensity) |
| `steps` | int \| None | Total daily step count |

**Algorithm:**

1. Sum `active_minutes` over the 7-day window; scale to 7-day equivalent (`total × 7 / n_days`). Compute `minutes_score` via `lerp` using anchors below.
2. Average `steps` across available days. Compute `steps_score` via `lerp` using anchors below.
3. Activity subscore = mean of whichever components are available.

**Active-minutes anchors** (weekly total):

| weekly active_minutes | score | Rationale |
|---|---|---|
| 0 | 10 | Completely sedentary |
| 75 | 50 | Half the WHO minimum (150 min/week); moderate risk |
| 150 | 85 | WHO minimum for adults; substantial benefit established |
| 300 | 100 | Double WHO minimum; upper bound of incremental gain |

**Steps anchors** (daily average):

| avg daily steps | score | Rationale |
|---|---|---|
| 2,000 | 20 | Functionally sedentary — equivalent to bedridden |
| 5,000 | 55 | Below the 7,500–10,000 step range linked to mortality reduction |
| 8,000 | 85 | Aligns with meta-analysis inflection point (~8,000 steps, Paluch 2022) |
| 12,000 | 100 | Diminishing returns above this; arbitrary ceiling |

**Fallback:** 30 (low-activity default).

---

### 2.3 Metabolic Subscore

**Inputs** (from the most recent `lab_panel` payload in `EHRRecord`):

| Field | Type | Notes |
|---|---|---|
| `hba1c_pct` | float \| None | Glycated haemoglobin (%) |
| `fasting_glucose_mmol` | float \| None | Fasting plasma glucose (mmol/L) |
| `crp_mg_l` | float \| None | C-reactive protein (mg/L) — inflammation marker |

**Algorithm:** Compute each signal's score independently via `lerp`; return the mean of available signals.

**HbA1c anchors:**

| hba1c_pct | score | Rationale |
|---|---|---|
| 5.0 | 100 | Well below prediabetes threshold; optimal |
| 5.7 | 85 | Top of normal range (ADA definition) |
| 6.4 | 55 | Upper bound of prediabetes range |
| 7.5 | 30 | Poorly controlled T2D; substantially elevated cardiovascular risk |
| 9.0 | 10 | Very poorly controlled; associated with micro- and macrovascular complications |

**Fasting glucose anchors:**

| fasting_glucose_mmol | score | Rationale |
|---|---|---|
| 4.5 | 100 | Optimal fasting glucose |
| 5.6 | 85 | Top of normal range (WHO/ADA) |
| 6.9 | 55 | IFG/prediabetes range upper boundary |
| 9.0 | 25 | Overt T2D; uncontrolled |

**CRP anchors:**

| crp_mg_l | score | Rationale |
|---|---|---|
| 0.5 | 100 | Minimal systemic inflammation |
| 1.0 | 90 | Low end of "average risk" band (hs-CRP) |
| 3.0 | 60 | Threshold for elevated cardiovascular risk (ACC/AHA) |
| 10 | 30 | High systemic inflammation; often concurrent acute illness |

**Fallback:** 65 (neutral; no labs on file).

---

### 2.4 Cardio Subscore

**Inputs** (from `lab_panel` + `WearableDay`):

| Field | Type | Notes |
|---|---|---|
| `sbp_mmhg` | float \| None | Systolic blood pressure (mmHg) |
| `ldl_mmol` | float \| None | LDL cholesterol (mmol/L) |
| `resting_hr_bpm` | int \| None | Resting heart rate (bpm) from wearable |

**Algorithm:** Compute each signal's score independently via `lerp`; average available signals. Resting HR is the 7-day mean over `SCORING_WINDOW_DAYS`.

**SBP anchors:**

| sbp_mmhg | score | Rationale |
|---|---|---|
| 110 | 100 | Ideal; well below ACC/AHA Stage 1 threshold |
| 120 | 90 | Normal upper bound |
| 130 | 70 | Elevated (ACC/AHA 2017 Stage 1 starts at 130) |
| 140 | 45 | Stage 2 hypertension threshold; substantially increased risk |
| 160 | 15 | Severe hypertension; treatment urgency |

**LDL anchors:**

| ldl_mmol | score | Rationale |
|---|---|---|
| 2.0 | 100 | Optimal; well below statin-target bands |
| 2.6 | 85 | Desirable per most European guidelines |
| 3.3 | 60 | Borderline high |
| 4.1 | 35 | High risk threshold |
| 5.0 | 15 | Very high; major cardiovascular risk factor |

**Resting HR anchors:**

| resting_hr_bpm | score | Rationale |
|---|---|---|
| 55 | 100 | Athlete-level; strong cardiac fitness |
| 60 | 90 | Excellent; consistent with high aerobic conditioning |
| 70 | 75 | Average healthy adult range |
| 80 | 55 | Moderately elevated; associated with higher CVD risk |
| 90 | 30 | Elevated resting HR; independent predictor of mortality |

**Fallback:** 65 (neutral; no cardiac data).

---

### 2.5 Lifestyle Subscore

**Inputs** (from `LifestyleProfile`):

| Field | Type | Notes |
|---|---|---|
| `diet_quality_score` | int \| None | Self-reported 1–10 diet quality |
| `exercise_sessions_weekly` | int \| None | Sessions per week |
| `stress_level` | int \| None | Self-reported 1–10 (1 = no stress) |
| `sleep_satisfaction` | int \| None | Self-reported 1–10 |

**Algorithm:** Compute each component; average available components.

**Diet:** `diet_quality_score × 10` (converts 1–10 scale to 0–100). Linear by design — the patient answered relative to their perceived optimum.

**Exercise anchors:**

| exercise_sessions_weekly | score | Rationale |
|---|---|---|
| 0 | 30 | No structured exercise; sedentary |
| 2 | 65 | Some activity; below recommended 3–5 sessions |
| 4 | 90 | Consistent; aligns with WHO physical activity guidelines |
| 6 | 100 | High frequency; ceiling |

**Stress (inverted) anchors:**

| stress_level | score | Rationale |
|---|---|---|
| 1 | 100 | No perceived stress; optimal |
| 5 | 60 | Moderate stress; impairs sleep, hormones, behaviour |
| 10 | 20 | Severe chronic stress; strongly correlated with cardiovascular and metabolic outcomes |

**Sleep satisfaction:** `sleep_satisfaction × 10` (converts 1–10 to 0–100). Captures subjective sleep quality independent of duration.

**Fallback:** 60 (neutral; no survey).

---

## 3. Composite Score

```
VitalityScore = 0.20 × Sleep
              + 0.20 × Activity
              + 0.20 × Metabolic
              + 0.25 × Cardio
              + 0.15 × Lifestyle
```

| Dimension | Weight | Rationale |
|---|---|---|
| Sleep | 0.20 | Sleep underpins metabolic regulation, immune function, and cognitive performance |
| Activity | 0.20 | Physical activity is the single strongest modifiable longevity predictor |
| Metabolic | 0.20 | Glycaemic control and inflammation drive long-term disease burden |
| Cardio | 0.25 | Cardiovascular disease is the leading cause of mortality in the target demographic |
| Lifestyle | 0.15 | Behaviour mediates the others but is lower-confidence (self-reported data) |

**Sum:** 1.00

**Clamping:** The composite is clamped to [0, 100] after the weighted sum. In practice, the weighted average of bounded subscores cannot exceed 100 or go below 0, but explicit clamping is a safety net.

---

## 4. Scoring Window vs Trend Window

Two time constants govern how wearable data is used:

| Constant | Value | Purpose |
|---|---|---|
| `SCORING_WINDOW_DAYS` | 7 | Days of wearable history used to compute sub-scores |
| `TREND_WINDOW_DAYS` | 30 | Days of history used to build the sparkline trend array |

**Why they differ:**

The **scoring window** should be short (7 days) because it represents *current state*. Using 30-day averages would lag too far behind genuine improvements or regressions — a patient who started a new sleep routine two weeks ago shouldn't see their score dragged down by old poor data.

The **trend window** should be long (30 days) because the sparkline is a *story*. A 7-point sparkline barely conveys direction; a 30-point arc makes a clear visual narrative of progress. The per-day trend score uses only the sleep and activity subscore blend (wearable-only, no lab data) to avoid the trend flattening whenever labs haven't changed.

**Implementation notes:**
- Sub-score functions receive a pre-filtered slice of `wearable` days of length `≤ SCORING_WINDOW_DAYS` (newest first).
- The trend array is computed separately over `≤ TREND_WINDOW_DAYS` of the most recent wearable rows.
- Both arrays are sorted newest-first in the `VitalityResult`.

---

## 5. Outlook Formula

```
Outlook(h) = current + (ceiling − current) × adherence × streak_mult(streak_days) × horizon_factor(h)
```

**Parameters:**

| Symbol | Value | Meaning |
|---|---|---|
| `ceiling` | 95.0 | Theoretical healthy upper bound; not a clinical target |
| `adherence` | completed_actions / total_actions, clamped [0, 1] | Protocol completion rate over the current streak |
| `streak_days` | int ≥ 0 | Consecutive days with ≥ 1 completed protocol action |
| `streak_mult(s)` | `1 − exp(−s / 30)` | Exponential saturation: 0 at s=0, 0.37 at s=11, 0.63 at s=30, 0.86 at s=60 |
| `horizon_factor(h)` | {3: 0.25, 6: 0.50, 12: 0.70} | Fraction of reachable gap captured by month h |

**Derivation of `streak_mult`:**

The function `1 − exp(−s/30)` is the standard saturating exponential used to model habit formation. The time constant τ = 30 days aligns with behavioural research suggesting ~4 weeks to stabilise a new routine. Key milestones:

| streak_days | streak_mult | Verbal description |
|---|---|---|
| 0 | 0.000 | Day zero — no streak, no multiplier |
| 7 | 0.206 | One week — early traction |
| 14 | 0.373 | Two weeks — building momentum |
| 30 | 0.632 | One month — half the exponential saturation |
| 60 | 0.865 | Two months — near plateau |
| 90 | 0.950 | Three months — almost full effect |

**Edge cases:**

- `streak_days ≤ 0` OR `adherence ≤ 0.0` → return `{h: float(current_score) for h in (3, 6, 12)}` — flat projection at current score.
- `current_score ≥ ceiling` → gap is 0 or negative; projections equal `ceiling` (effectively clamped at ceiling).
- Final clamp: `projected = max(current_score, min(ceiling, current_score + gain))` — never goes below current, never exceeds ceiling.

---

## 6. Worked Example — Rebecca (PT0199)

Rebecca is a 44-year-old with managed Type 2 Diabetes who has completed 90 days of her longevity protocol. The following inputs reflect her 7-day mean wearable readings and most recent labs on 2026-04-10.

### 6.1 Inputs

**Wearable (7-day mean ending 2026-04-10):**

| Signal | Value |
|---|---|
| `steps` | 9,200/day |
| `active_minutes` | 33/day (= 231/week) |
| `sleep_duration_hrs` | 7.4 h |
| `sleep_quality_score` | 82 |
| `deep_sleep_pct` | 21% |
| `resting_hr_bpm` | 65 bpm |
| `hrv_rmssd_ms` | 52 ms |

**Labs (most recent `lab_panel`):**

| Signal | Value |
|---|---|
| `hba1c_pct` | 6.5% |
| `fasting_glucose_mmol` | 7.4 mmol/L |
| `sbp_mmhg` | 132 mmHg |
| `ldl_mmol` | 2.9 mmol/L |
| `crp_mg_l` | 1.8 mg/L |

**Lifestyle survey (2026-04-05):**

| Signal | Value |
|---|---|
| `diet_quality_score` | 8 |
| `exercise_sessions_weekly` | 5 |
| `stress_level` | 4 |
| `sleep_satisfaction` | 8 |

**Outlook inputs:**
- `streak_days` = 14
- `adherence` = 0.85

---

### 6.2 Sleep Subscore

**Step 1 — Duration score (`sleep_duration_hrs = 7.4`):**

Anchors in range: (6 → 55) and (7.5 → 95)

```
f = (7.4 − 6.0) / (7.5 − 6.0) = 1.4 / 1.5 = 0.933
duration_score = 55 + 0.933 × (95 − 55) = 55 + 37.3 = 92.3
```

**Step 2 — Average with quality score (`sleep_quality_score = 82`):**

```
quality_avg = (92.3 + 82.0) / 2 = 87.2
```

**Step 3 — Deep-sleep bonus (`deep_sleep_pct = 21% ≥ 20%`):**

```
sleep_subscore = 87.2 + 5 = 92.2
```

---

### 6.3 Activity Subscore

**Active-minutes component (33/day × 7 = 231 min/week):**

Anchors in range: (150 → 85) and (300 → 100)

```
f = (231 − 150) / (300 − 150) = 81 / 150 = 0.54
minutes_score = 85 + 0.54 × (100 − 85) = 85 + 8.1 = 93.1
```

**Steps component (9,200 steps/day):**

Anchors in range: (8,000 → 85) and (12,000 → 100)

```
f = (9200 − 8000) / (12000 − 8000) = 1200 / 4000 = 0.30
steps_score = 85 + 0.30 × (100 − 85) = 85 + 4.5 = 89.5
```

**Activity subscore:**

```
activity_subscore = (93.1 + 89.5) / 2 = 91.3
```

---

### 6.4 Metabolic Subscore

**HbA1c component (`hba1c_pct = 6.5`):**

Anchors in range: (6.4 → 55) and (7.5 → 30)

```
f = (6.5 − 6.4) / (7.5 − 6.4) = 0.1 / 1.1 = 0.091
hba1c_score = 55 + 0.091 × (30 − 55) = 55 − 2.3 = 52.7
```

**Fasting glucose component (`fasting_glucose_mmol = 7.4`):**

Anchors in range: (6.9 → 55) and (9.0 → 25)

```
f = (7.4 − 6.9) / (9.0 − 6.9) = 0.5 / 2.1 = 0.238
glucose_score = 55 + 0.238 × (25 − 55) = 55 − 7.1 = 47.9
```

**CRP component (`crp_mg_l = 1.8`):**

Anchors in range: (1.0 → 90) and (3.0 → 60)

```
f = (1.8 − 1.0) / (3.0 − 1.0) = 0.8 / 2.0 = 0.40
crp_score = 90 + 0.40 × (60 − 90) = 90 − 12.0 = 78.0
```

**Metabolic subscore:**

```
metabolic_subscore = (52.7 + 47.9 + 78.0) / 3 = 178.6 / 3 = 59.5
```

The metabolic subscore reflects Rebecca's managed-but-not-resolved T2D — her HbA1c (6.5%) and fasting glucose (7.4 mmol/L) are still in the diabetic range, which honestly constrains this subscore.

---

### 6.5 Cardio Subscore

**SBP component (`sbp_mmhg = 132`):**

Anchors in range: (130 → 70) and (140 → 45)

```
f = (132 − 130) / (140 − 130) = 2 / 10 = 0.20
sbp_score = 70 + 0.20 × (45 − 70) = 70 − 5.0 = 65.0
```

**LDL component (`ldl_mmol = 2.9`):**

Anchors in range: (2.6 → 85) and (3.3 → 60)

```
f = (2.9 − 2.6) / (3.3 − 2.6) = 0.3 / 0.7 = 0.429
ldl_score = 85 + 0.429 × (60 − 85) = 85 − 10.7 = 74.3
```

**Resting HR component (`resting_hr_bpm = 65`):**

Anchors in range: (60 → 90) and (70 → 75)

```
f = (65 − 60) / (70 − 60) = 5 / 10 = 0.50
resting_hr_score = 90 + 0.50 × (75 − 90) = 90 − 7.5 = 82.5
```

**Cardio subscore:**

```
cardio_subscore = (65.0 + 74.3 + 82.5) / 3 = 221.8 / 3 = 73.9
```

---

### 6.6 Lifestyle Subscore

| Component | Computation | Result |
|---|---|---|
| Diet (`diet_quality_score = 8`) | 8 × 10 | 80.0 |
| Exercise (`exercise_sessions_weekly = 5`) | lerp(4→90, 6→100) at 5: 90 + 0.5×10 | 95.0 |
| Stress (`stress_level = 4`, inverted) | lerp(1→100, 5→60) at 4: 100 + 0.75×(60−100) | 70.0 |
| Sleep satisfaction (`sleep_satisfaction = 8`) | 8 × 10 | 80.0 |

```
lifestyle_subscore = (80.0 + 95.0 + 70.0 + 80.0) / 4 = 325.0 / 4 = 81.25
```

---

### 6.7 Composite Score

| Dimension | Subscore | Weight | Contribution |
|---|---|---|---|
| Sleep | 92.2 | 0.20 | 18.44 |
| Activity | 91.3 | 0.20 | 18.26 |
| Metabolic | 59.5 | 0.20 | 11.90 |
| Cardio | 73.9 | 0.25 | 18.48 |
| Lifestyle | 81.3 | 0.15 | 12.19 |
| **Total** | | **1.00** | **79.3** |

```
VitalityScore = 0.20 × 92.2 + 0.20 × 91.3 + 0.20 × 59.5 + 0.25 × 73.9 + 0.15 × 81.3
              = 18.44 + 18.26 + 11.90 + 18.48 + 12.19
              = 79.3
```

**Interpretation:** Rebecca scores in the high-70s. Her excellent sleep, activity, and lifestyle habits after 90 days of protocol adherence pull the score up strongly. The metabolic subscore (59.5) reflects the honest reality that her T2D is managed but not resolved — her HbA1c and fasting glucose still sit in the diabetic range and cannot be improved by behaviour alone in 7 days. This creates a meaningful gap between her behavioural subscores (~80–92) and her metabolic reality (~60), which the formula surfaces correctly.

> **Calibration note for T3/T7:** The planning document mentioned a "~65" composite target for Rebecca. That estimate was made before the anchors were finalized. The formula with these inputs produces ~79.3, which accurately reflects her day-90 trajectory. If the integration test band needs adjustment, update the assertion in `test_rebecca_showcase.py` rather than tuning the anchors to hit a round number.

---

### 6.8 Outlook Projection

**Inputs:** current = 79.3, ceiling = 95.0, streak_days = 14, adherence = 0.85

**Step 1 — Streak multiplier:**

```
streak_mult(14) = 1 − exp(−14 / 30)
               = 1 − exp(−0.467)
               = 1 − 0.627
               = 0.373
```

**Step 2 — Reachable gap:**

```
gap = ceiling − current = 95.0 − 79.3 = 15.7
```

**Step 3 — Per-horizon projections:**

| Horizon (months) | horizon_factor | gain = gap × adherence × streak_mult × hf | projected |
|---|---|---|---|
| 3 | 0.25 | 15.7 × 0.85 × 0.373 × 0.25 = **1.25** | **80.5** |
| 6 | 0.50 | 15.7 × 0.85 × 0.373 × 0.50 = **2.49** | **81.8** |
| 12 | 0.70 | 15.7 × 0.85 × 0.373 × 0.70 = **3.49** | **82.8** |

**Reading the numbers:** Rebecca is already performing well (79.3), so the absolute point gains are modest (1–4 points). The outlook communicates *proportional progress toward her ceiling* rather than large jumps. If she extended her streak to 60 days (streak_mult = 0.865), the same adherence would project +2.9 / +5.8 / +8.1 points — a more compelling visual at the 6- and 12-month horizons.

---

## 7. Reasoning and Trade-offs

### Why piecewise-linear interpolation?

**The alternative — step functions (buckets):** The prior v1 engine used step functions (`if hba1c < 5.7: 100; elif hba1c <= 6.4: 60; else: 30`). Buckets are easy to implement but create discontinuities: a patient who improves HbA1c from 6.5 to 6.3 crosses a bucket boundary and sees a 30-point jump. That makes the score feel gameable and hard to explain ("why did my score jump 30 points from a 0.2% lab change?").

**Piecewise-linear:** A 0.2% HbA1c improvement yields a proportional score improvement (~2 points). The response curve is smooth and explainable. Anchors still capture the clinical thresholds that matter (5.7, 6.4, 7.5) as inflection points — they just don't create discontinuities.

**Why not sigmoid or logistic?** Sigmoids are harder to reason about ("why is the curve steeper here?") and the calibration requires fitting data we don't have. Piecewise-linear with explicit anchors lets any team member read the formula table and understand exactly where their score sits without a calculator.

### Why a capped-ceiling model for outlook?

**The alternative — additive-streak-weight:** The prior v1 engine added a linear streak bonus to the current score. That formulation can project above 100 if the streak is long enough, and the semantics are unclear ("what does +15 points mean for a patient already at 90?").

**The capped-ceiling model** operates on the *remaining gap to the ceiling*. This has three natural properties:
1. **Bounded by construction** — the result always lies in [current, 95].
2. **Diminishing returns** — patients already near the ceiling see small projected gains; patients with room to improve see larger gains. This is honest.
3. **Exponential streak** — the first weeks of a streak are the most impactful (captures the intuition that starting is the hardest part). A patient who has stuck with the protocol for 30 days has unlocked 63% of the streak multiplier; at 60 days, 86%.

### Why these specific weights?

The composite weights (sleep 0.20, activity 0.20, metabolic 0.20, cardio 0.25, lifestyle 0.15) were chosen to reflect the relative contribution of each dimension to all-cause mortality and disability-adjusted life years in middle-aged European adults (based on GBD 2019 attribution estimates). Cardio receives the highest weight (0.25) because cardiovascular disease is the leading cause of premature mortality in the target demographic. Lifestyle receives the lowest weight (0.15) because it is self-reported and thus lower-confidence; it also partially mediates the other four.

These weights are heuristic and will be recalibrated with outcomes data in v2.

### What this formula does not capture

- **Trend direction within the scoring window** — a patient whose score is improving vs one whose score is stable at the same value look identical. The trend sparkline (not the score) communicates direction.
- **Medication adherence and treatment compliance** — not in the data model yet.
- **Mental health beyond stress level** — the WHO-5 mental wellbeing score is collected in the survey but not yet a direct subscore input.
- **Lab trend over time** — one lab panel is used; if a patient has multiple panels showing improvement, only the latest counts.

These are known limitations, not bugs. They are candidates for v2.
