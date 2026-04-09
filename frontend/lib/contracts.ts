export type TabKey = "today" | "coach" | "records" | "insights" | "care" | "me";
export type DataMode = "live" | "demo";

export interface HealthResponse {
  status: string;
}

export interface PatientProfileOut {
  patient_id: string;
  name: string;
  age: number;
  country: string;
  sex: string | null;
  bmi: number | null;
  smoking_status: string | null;
  height_cm: number | null;
  weight_kg: number | null;
}

export interface TrendPoint {
  date: string;
  score: number;
}

export interface VitalityOut {
  score: number;
  subscores: Record<string, number>;
  trend: TrendPoint[];
  computed_at: string;
  risk_flags: string[];
  disclaimer: string;
}

export interface WearableDayOut {
  patient_id: string;
  date: string;
  resting_hr_bpm: number | null;
  hrv_rmssd_ms: number | null;
  steps: number | null;
  active_minutes: number | null;
  calories_burned_kcal: number | null;
  sleep_duration_hrs: number | null;
  sleep_quality_score: number | null;
  deep_sleep_pct: number | null;
  spo2_avg_pct: number | null;
}

export interface WearableSeriesOut {
  patient_id: string;
  days: WearableDayOut[];
}

export interface EHRRecordOut {
  id: number;
  record_type: string;
  recorded_at: string;
  payload: Record<string, unknown>;
  source: string;
}

export interface EHRRecordListOut {
  patient_id: string;
  records: EHRRecordOut[];
  total: number;
}

export interface InsightOut {
  kind: string;
  severity: "low" | "moderate" | "high";
  message: string;
  signals: string[];
  prevention_signals: string[];
  disclaimer: string;
}

export interface InsightsListOut {
  patient_id: string;
  insights: InsightOut[];
  risk_flags: string[];
  signals: string[];
  prevention_signals: string[];
}

export interface AppointmentOut {
  id: string;
  title: string;
  provider: string;
  location: string;
  starts_at: string;
  duration_minutes: number;
  price_eur: number | null;
  covered_percent: number | null;
}

export interface AppointmentListOut {
  patient_id: string;
  appointments: AppointmentOut[];
}

export interface BackendStatus {
  title: string;
  detail: string;
  reachable: boolean;
  authenticated: boolean;
}

export interface AppBootstrap {
  patientId: string;
  source: DataMode;
  health: HealthResponse | null;
  backendStatus: BackendStatus;
  profile: PatientProfileOut;
  vitality: VitalityOut;
  wearable: WearableSeriesOut;
  records: EHRRecordListOut;
  insights: InsightsListOut;
  appointments: AppointmentListOut;
}

export const NAV_ITEMS = [
  { key: "today", label: "Today" },
  { key: "coach", label: "Coach" },
  { key: "records", label: "Records" },
  { key: "insights", label: "Insights" },
  { key: "care", label: "Care" },
  { key: "me", label: "Me" },
] as const satisfies readonly { key: TabKey; label: string }[];

export const ROUTE_GROUPS: Record<
  TabKey,
  { title: string; note: string; routes: string[] }
> = {
  today: {
    title: "Slice 1 data already shipped",
    note: "Today stays grounded in the read-only backend that already exists in this repo.",
    routes: [
      "GET /healthz",
      "GET /patients/{patient_id}/profile",
      "GET /patients/{patient_id}/vitality",
      "GET /patients/{patient_id}/wearable",
    ],
  },
  coach: {
    title: "Reserved for slice 2",
    note: "No coach, protocol, meal vision, or chat backend route exists yet, so this tab is intentionally shallow.",
    routes: [],
  },
  records: {
    title: "Provider data surface",
    note: "Records reads from the shipped EHR endpoint and avoids any AI Q&A contract until slice 2 is built.",
    routes: ["GET /patients/{patient_id}/records"],
  },
  insights: {
    title: "Signals and wellness flags",
    note: "Insights is mapped directly to the derived signal endpoint from the current FastAPI backend.",
    routes: ["GET /patients/{patient_id}/insights"],
  },
  care: {
    title: "Care label mapped to appointments",
    note: "The product tab is Care, but the live slice 1 backend surface underneath it is appointments.",
    routes: ["GET /patients/{patient_id}/appointments"],
  },
  me: {
    title: "Profile and privacy controls",
    note: "Me uses existing profile and GDPR routes without inventing any new account backend.",
    routes: [
      "GET /patients/{patient_id}/profile",
      "GET /patients/{patient_id}/gdpr/export",
      "DELETE /patients/{patient_id}/gdpr",
    ],
  },
};
