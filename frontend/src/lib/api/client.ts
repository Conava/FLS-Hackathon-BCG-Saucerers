/**
 * Typed API client for the Longevity+ backend.
 *
 * Every method calls `/api/proxy/<path>` — never the FastAPI backend directly.
 * The Next.js proxy route handler rewrites the request and injects the
 * patient_id from the httpOnly cookie.
 *
 * Stack: Next.js 15, global fetch (no node-fetch).
 */

import type {
  PatientProfileOut,
  VitalityOut,
  WearableSeriesOut,
  OutlookOut,
  OutlookNarratorResponse,
  InsightsListOut,
  FutureSelfResponse,
  ProtocolOut,
  ProtocolActionOut,
  CompleteActionResponse,
  DailyLogListOut,
  DailyLogOut,
  MealLogListOut,
  MealLogUploadResponse,
  ManualMealLogInput,
  ChatChunk,
  EHRRecordListOut,
  RecordsQAResponse,
  SurveyHistoryOut,
  SurveyResponseOut,
  AppointmentListOut,
  AppointmentOut,
  ClinicalReviewResponse,
  ReferralResponse,
  MessageListOut,
  MessageOut,
  SmartNotificationResponse,
  GDPRExportOut,
  GDPRDeleteAck,
} from "./schemas";

/** Base path for all proxy requests. */
const PROXY_BASE = "/api/proxy";

/** Fetch wrapper — throws on non-2xx responses. */
async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${PROXY_BASE}/${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Patient
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id} — demographic profile. */
export async function getPatientProfile(): Promise<PatientProfileOut> {
  return request<PatientProfileOut>("profile");
}

// ---------------------------------------------------------------------------
// Vitality
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/vitality — heuristic vitality score. */
export async function getVitality(): Promise<VitalityOut> {
  return request<VitalityOut>("vitality");
}

// ---------------------------------------------------------------------------
// Wearable
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/wearable — wearable telemetry series. */
export async function getWearable(): Promise<WearableSeriesOut> {
  return request<WearableSeriesOut>("wearable");
}

// ---------------------------------------------------------------------------
// Outlook
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/outlook — stored outlook entry. */
export async function getOutlook(): Promise<OutlookOut> {
  return request<OutlookOut>("outlook");
}

/** POST /v1/patients/{patient_id}/outlook-narrator — AI-generated narrative. */
export async function postOutlookNarrator(body: {
  patient_id: string;
  horizon_months?: number;
  top_drivers?: string[];
}): Promise<OutlookNarratorResponse> {
  return request<OutlookNarratorResponse>("outlook-narrator", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Insights
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/insights — wellness insights list. */
export async function getInsights(): Promise<InsightsListOut> {
  return request<InsightsListOut>("insights");
}

// ---------------------------------------------------------------------------
// Future Self
// ---------------------------------------------------------------------------

/** POST /v1/patients/{patient_id}/future-self — lifestyle projection. */
export async function postFutureSelf(body: {
  patient_id: string;
  sliders?: Record<string, unknown>;
}): Promise<FutureSelfResponse> {
  return request<FutureSelfResponse>("future-self", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Protocol
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/protocol — active protocol. */
export async function getProtocol(): Promise<ProtocolOut> {
  return request<ProtocolOut>("protocol");
}

/** POST /v1/patients/{patient_id}/protocol/generate — generate a new protocol. */
export async function generateProtocol(): Promise<ProtocolOut> {
  return request<ProtocolOut>("protocol/generate", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

/** POST /v1/patients/{patient_id}/protocol/complete-action — mark action complete. */
export async function completeProtocolAction(
  actionId: number,
): Promise<CompleteActionResponse> {
  return request<CompleteActionResponse>("protocol/complete-action", {
    method: "POST",
    body: JSON.stringify({ action_id: actionId }),
  });
}

// ---------------------------------------------------------------------------
// Daily Log
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/daily-log — list entries for a date range. */
export async function getDailyLogs(params: {
  from: string;
  to: string;
}): Promise<DailyLogListOut> {
  const qs = new URLSearchParams({ from: params.from, to: params.to });
  return request<DailyLogListOut>(`daily-log?${qs.toString()}`);
}

/**
 * POST /v1/patients/{patient_id}/daily-log — create a log entry.
 *
 * Extended with structured sleep quality (B1), workout type/intensity (B1),
 * and water intake in millilitres (B4).
 */
export async function createDailyLog(body: {
  date: string;
  mood_score?: number | null;
  sleep_hours?: number | null;
  /** Sleep quality score 1–5 (B1). */
  sleep_quality?: number | null;
  workout_minutes?: number | null;
  /** Workout type: walk|run|bike|strength|yoga|other (B1). */
  workout_type?: string | null;
  /** Workout intensity: low|med|high (B1). */
  workout_intensity?: string | null;
  water_glasses?: number | null;
  /** Water intake in millilitres (B4). */
  water_ml?: number | null;
  alcohol_units?: number | null;
}): Promise<DailyLogOut> {
  return request<DailyLogOut>("daily-log", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Meal Log
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/meal-log — list meal log entries. */
export async function getMealLogs(): Promise<MealLogListOut> {
  return request<MealLogListOut>("meal-log");
}

/**
 * POST /v1/patients/{patient_id}/meal-log — upload a meal photo.
 *
 * Sends a multipart/form-data body — do NOT set Content-Type manually;
 * the browser sets the correct boundary automatically.
 */
export async function uploadMealLog(formData: FormData): Promise<MealLogUploadResponse> {
  const url = `${PROXY_BASE}/meal-log`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<MealLogUploadResponse>;
}

// ---------------------------------------------------------------------------
// Coach / Chat (SSE)
// ---------------------------------------------------------------------------

/**
 * POST /v1/patients/{patient_id}/coach/chat — streaming AI coach response.
 *
 * Returns an `AsyncIterable<ChatChunk>` that yields parsed SSE events.
 * Each event has `event` ("token" | "done" | "error") and `data` (string).
 *
 * Usage:
 * ```ts
 * for await (const chunk of coachChat({ message: "Hello" })) {
 *   if (chunk.event === "token") appendText(chunk.data);
 *   if (chunk.event === "done") break;
 * }
 * ```
 */
export async function* coachChat(body: {
  message: string;
  history?: Array<{ role: string; content: string }>;
}): AsyncIterable<ChatChunk> {
  const url = `${PROXY_BASE}/coach/chat`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${text}`);
  }

  if (!res.body) {
    throw new Error("No response body for SSE stream");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const events = buffer.split("\n\n");
      // Keep the last (potentially incomplete) chunk in the buffer
      buffer = events.pop() ?? "";

      for (const raw of events) {
        if (!raw.trim()) continue;

        let event = "message";
        let data = "";

        for (const line of raw.split("\n")) {
          if (line.startsWith("event: ")) {
            event = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            data = line.slice(6).trim();
          }
        }

        yield { event: event as ChatChunk["event"], data };
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ---------------------------------------------------------------------------
// EHR Records
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/records — paginated EHR record list. */
export async function getRecords(params?: {
  limit?: number;
  offset?: number;
  record_type?: string;
}): Promise<EHRRecordListOut> {
  const qs = new URLSearchParams();
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  if (params?.record_type) qs.set("record_type", params.record_type);
  const query = qs.toString();
  return request<EHRRecordListOut>(`records${query ? `?${query}` : ""}`);
}

/** POST /v1/patients/{patient_id}/records/qa — EHR Q&A. */
export async function postRecordsQA(question: string): Promise<RecordsQAResponse> {
  return request<RecordsQAResponse>("records/qa", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

// ---------------------------------------------------------------------------
// Survey
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/survey — survey submission history. */
export async function getSurveyHistory(): Promise<SurveyHistoryOut> {
  return request<SurveyHistoryOut>("survey");
}

/** POST /v1/patients/{patient_id}/survey — submit a survey. */
export async function submitSurvey(body: {
  kind: "onboarding" | "weekly" | "quarterly";
  answers?: Record<string, unknown>;
}): Promise<SurveyResponseOut> {
  return request<SurveyResponseOut>("survey", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Appointments
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/appointments/ — list upcoming appointments. */
export async function getAppointments(): Promise<AppointmentListOut> {
  return request<AppointmentListOut>("appointments/");
}

/** POST /v1/patients/{patient_id}/appointments/ — book an appointment. */
export async function bookAppointment(body: {
  title: string;
  provider: string;
  location: string;
  starts_at: string;
  duration_minutes: number;
  price_eur?: number | null;
  covered_percent?: number | null;
}): Promise<AppointmentOut> {
  return request<AppointmentOut>("appointments/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Clinical Review
// ---------------------------------------------------------------------------

/** POST /v1/patients/{patient_id}/clinical-review — create a review request. */
export async function createClinicalReview(body: {
  patient_id: string;
  notes: string;
}): Promise<ClinicalReviewResponse> {
  return request<ClinicalReviewResponse>("clinical-review", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Referral
// ---------------------------------------------------------------------------

/** POST /v1/patients/{patient_id}/referral — create a referral. */
export async function createReferral(body: {
  patient_id: string;
  specialty: string;
  reason: string;
}): Promise<ReferralResponse> {
  return request<ReferralResponse>("referral", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/messages — list in-app messages. */
export async function getMessages(): Promise<MessageListOut> {
  return request<MessageListOut>("messages");
}

/** POST /v1/patients/{patient_id}/messages — send a message. */
export async function sendMessage(body: {
  patient_id: string;
  content: string;
}): Promise<MessageOut> {
  return request<MessageOut>("messages", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Smart Notifications
// ---------------------------------------------------------------------------

/** POST /v1/patients/{patient_id}/notifications/smart — generate a smart push. */
export async function createSmartNotification(body: {
  trigger_kind: string;
  context?: Record<string, unknown>;
}): Promise<SmartNotificationResponse> {
  return request<SmartNotificationResponse>("notifications/smart", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// GDPR
// ---------------------------------------------------------------------------

/** GET /v1/patients/{patient_id}/gdpr/export — Art. 15 data export. */
export async function getGDPRExport(): Promise<GDPRExportOut> {
  return request<GDPRExportOut>("gdpr/export");
}

/** DELETE /v1/patients/{patient_id}/gdpr — Art. 17 erasure request. */
export async function requestGDPRDelete(): Promise<GDPRDeleteAck> {
  return request<GDPRDeleteAck>("gdpr", {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Manual Meal Log (B2/B4)
// ---------------------------------------------------------------------------

/**
 * POST /v1/patients/{patient_id}/meal-log/manual — log a meal without a photo.
 *
 * Stores the entry in the `meal_log` table using a `manual://<uuid>` sentinel
 * photo_uri so it appears alongside photo entries in the meal history.
 */
export async function createManualMealLog(
  body: ManualMealLogInput,
): Promise<MealLogUploadResponse> {
  return request<MealLogUploadResponse>("meal-log/manual", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Protocol Skip + Reorder (B3/B4)
// ---------------------------------------------------------------------------

/**
 * POST /v1/patients/{patient_id}/protocol/skip-action — skip an action with reason.
 *
 * Sets `skipped_today=true` and records the reason. Does not affect the streak
 * or outlook score — skipped is distinct from missed.
 */
export async function skipProtocolAction(
  actionId: number,
  reason: string,
): Promise<ProtocolActionOut> {
  return request<ProtocolActionOut>("protocol/skip-action", {
    method: "POST",
    body: JSON.stringify({ action_id: actionId, reason }),
  });
}

/**
 * POST /v1/patients/{patient_id}/protocol/reorder — persist a new action order.
 *
 * Sends the full ordered list of action IDs; the backend writes `sort_order =
 * index` for each. Returns 204 No Content on success — the caller should
 * apply optimistic state locally and roll back on error.
 */
export async function reorderProtocolActions(
  actionIds: number[],
): Promise<void> {
  await request<unknown>("protocol/reorder", {
    method: "POST",
    body: JSON.stringify({ action_ids: actionIds }),
  });
}

// ---------------------------------------------------------------------------
// Weekly Check-in (B4)
// ---------------------------------------------------------------------------

/**
 * POST /v1/patients/{patient_id}/survey — submit the weekly check-in.
 *
 * Reuses the existing `submitSurvey` shape with `kind: "weekly"`.
 * Accepts the three standard weekly questions: energy, sleep, mood (all 1–5).
 */
export async function submitWeeklyCheckIn(answers: {
  energy: number;
  sleep: number;
  mood: number;
}): Promise<SurveyResponseOut> {
  return request<SurveyResponseOut>("survey", {
    method: "POST",
    body: JSON.stringify({ kind: "weekly", answers }),
  });
}
