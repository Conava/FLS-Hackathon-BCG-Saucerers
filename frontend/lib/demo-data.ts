import type { AppBootstrap } from "@/lib/contracts";

const DISCLAIMER = "Wellness signal, not medical advice.";

export function createDemoBootstrap(patientId = "PT0282"): AppBootstrap {
  return {
    patientId,
    source: "demo",
    health: null,
    backendStatus: {
      title: "Demo snapshot active",
      detail:
        "The shell is using a local slice 1 snapshot so the mobile nav can run before the frontend has deeper backend support.",
      reachable: false,
      authenticated: false,
    },
    profile: {
      patient_id: patientId,
      name: "Anna Weber",
      age: 43,
      country: "Germany",
      sex: "female",
      bmi: 22.7,
      smoking_status: "never",
      height_cm: 168,
      weight_kg: 64,
    },
    vitality: {
      score: 68,
      subscores: {
        sleep: 61,
        activity: 74,
        metabolic: 66,
        cardio: 64,
        lifestyle: 77,
      },
      trend: [
        { date: "2026-04-03", score: 74 },
        { date: "2026-04-04", score: 76 },
        { date: "2026-04-05", score: 73 },
        { date: "2026-04-06", score: 75 },
        { date: "2026-04-07", score: 72 },
        { date: "2026-04-08", score: 70 },
        { date: "2026-04-09", score: 68 },
      ],
      computed_at: "2026-04-09T07:40:00",
      risk_flags: ["elevated_ldl", "short_sleep", "resting_hr_above_baseline"],
      disclaimer: DISCLAIMER,
    },
    wearable: {
      patient_id: patientId,
      days: [
        {
          patient_id: patientId,
          date: "2026-04-09",
          resting_hr_bpm: 68,
          hrv_rmssd_ms: 29,
          steps: 4730,
          active_minutes: 24,
          calories_burned_kcal: 1870,
          sleep_duration_hrs: 5.7,
          sleep_quality_score: 62,
          deep_sleep_pct: 13,
          spo2_avg_pct: 97,
        },
        {
          patient_id: patientId,
          date: "2026-04-08",
          resting_hr_bpm: 66,
          hrv_rmssd_ms: 32,
          steps: 5980,
          active_minutes: 38,
          calories_burned_kcal: 1955,
          sleep_duration_hrs: 6.1,
          sleep_quality_score: 67,
          deep_sleep_pct: 15,
          spo2_avg_pct: 98,
        },
        {
          patient_id: patientId,
          date: "2026-04-07",
          resting_hr_bpm: 64,
          hrv_rmssd_ms: 36,
          steps: 8200,
          active_minutes: 54,
          calories_burned_kcal: 2080,
          sleep_duration_hrs: 7.2,
          sleep_quality_score: 78,
          deep_sleep_pct: 18,
          spo2_avg_pct: 98,
        },
      ],
    },
    records: {
      patient_id: patientId,
      total: 2,
      records: [
        {
          id: 101,
          record_type: "lab_panel",
          recorded_at: "2025-11-14T08:30:00",
          payload: {
            total_cholesterol_mmol: 7.05,
            ldl_mmol: 3.84,
            hdl_mmol: 1.62,
            triglycerides_mmol: 1.1,
            sbp_mmhg: 128,
          },
          source: "csv",
        },
        {
          id: 102,
          record_type: "visit",
          recorded_at: "2025-06-11T10:15:00",
          payload: {
            provider: "Dr. Kessler",
            notes:
              "Family history noted and prevention-focused lipid follow-up suggested.",
          },
          source: "csv",
        },
      ],
    },
    insights: {
      patient_id: patientId,
      risk_flags: ["elevated_ldl", "sleep_debt"],
      signals: [
        "LDL above the optimal range in the last lipid panel",
        "Three recent nights below 7 hours of sleep",
      ],
      prevention_signals: [
        "Discuss a prevention panel in Care",
        "Protect recovery with a lighter movement day",
      ],
      insights: [
        {
          kind: "lipid",
          severity: "high",
          message:
            "Elevated cholesterol markers are the strongest current prevention signal in Anna's profile.",
          signals: ["LDL 3.84 mmol/L", "Total cholesterol 7.05 mmol/L"],
          prevention_signals: [
            "Schedule the cardio-prevention panel",
            "Shift lunch carbs toward higher-fiber swaps",
          ],
          disclaimer: DISCLAIMER,
        },
        {
          kind: "sleep",
          severity: "moderate",
          message:
            "Recent under-recovery is suppressing the vitality trend and nudging resting heart rate upward.",
          signals: ["Sleep 5.7h", "Resting HR +6 bpm vs. baseline"],
          prevention_signals: [
            "Reduce intensity today",
            "Prioritise lights-out earlier tonight",
          ],
          disclaimer: DISCLAIMER,
        },
      ],
    },
    appointments: {
      patient_id: patientId,
      appointments: [
        {
          id: "appt-pt0282-cardio",
          title: "Cardio-Prevention Panel",
          provider: "Dr. Mehlhorn",
          location: "Hamburg-Eppendorf",
          starts_at: "2026-04-14T14:30:00",
          duration_minutes: 45,
          price_eur: 79,
          covered_percent: 80,
        },
        {
          id: "appt-pt0282-sleep",
          title: "Sleep Assessment",
          provider: "Dr. Klein",
          location: "Tele-consult",
          starts_at: "2026-04-17T09:00:00",
          duration_minutes: 30,
          price_eur: 45,
          covered_percent: 80,
        },
      ],
    },
  };
}
