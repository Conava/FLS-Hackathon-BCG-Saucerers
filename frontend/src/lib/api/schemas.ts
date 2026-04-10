/**
 * Zod schemas derived from the backend OpenAPI spec (openapi.json).
 *
 * All schemas use .passthrough() so that backend additions don't break
 * the UI. TypeScript types are derived via z.infer<typeof Schema>.
 *
 * Stack: Next.js 15 App Router + Zod v3
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Shared building blocks
// ---------------------------------------------------------------------------

/** Non-PHI observability metadata for a single LLM call. */
export const AIMetaSchema = z
  .object({
    model: z.string(),
    prompt_name: z.string(),
    request_id: z.string(),
    token_in: z.number().int(),
    token_out: z.number().int(),
    latency_ms: z.number().int(),
  })
  .passthrough();

export type AIMeta = z.infer<typeof AIMetaSchema>;

// ---------------------------------------------------------------------------
// Patient
// ---------------------------------------------------------------------------

export const PatientProfileOutSchema = z
  .object({
    patient_id: z.string(),
    name: z.string(),
    age: z.number().int(),
    country: z.string(),
    sex: z.string().nullish(),
    bmi: z.number().nullish(),
    height_cm: z.number().nullish(),
    weight_kg: z.number().nullish(),
    smoking_status: z.string().nullish(),
  })
  .passthrough();

export type PatientProfileOut = z.infer<typeof PatientProfileOutSchema>;

// ---------------------------------------------------------------------------
// Vitality
// ---------------------------------------------------------------------------

export const TrendPointSchema = z
  .object({
    date: z.string(),
    score: z.number(),
  })
  .passthrough();

export type TrendPoint = z.infer<typeof TrendPointSchema>;

export const VitalityOutSchema = z
  .object({
    score: z.number(),
    subscores: z.record(z.number()),
    computed_at: z.string(),
    disclaimer: z.string().optional(),
    risk_flags: z.array(z.string()).optional(),
    trend: z.array(TrendPointSchema).optional(),
  })
  .passthrough();

export type VitalityOut = z.infer<typeof VitalityOutSchema>;

// ---------------------------------------------------------------------------
// Wearable
// ---------------------------------------------------------------------------

export const WearableDayOutSchema = z
  .object({
    patient_id: z.string(),
    date: z.string(),
    steps: z.number().int().nullish(),
    active_minutes: z.number().int().nullish(),
    calories_burned_kcal: z.number().nullish(),
    resting_hr_bpm: z.number().nullish(),
    hrv_rmssd_ms: z.number().nullish(),
    spo2_avg_pct: z.number().nullish(),
    sleep_duration_hrs: z.number().nullish(),
    sleep_quality_score: z.number().int().nullish(),
    deep_sleep_pct: z.number().nullish(),
  })
  .passthrough();

export type WearableDayOut = z.infer<typeof WearableDayOutSchema>;

export const WearableSeriesOutSchema = z
  .object({
    patient_id: z.string(),
    days: z.array(WearableDayOutSchema).optional(),
  })
  .passthrough();

export type WearableSeriesOut = z.infer<typeof WearableSeriesOutSchema>;

// ---------------------------------------------------------------------------
// Outlook
// ---------------------------------------------------------------------------

export const OutlookOutSchema = z
  .object({
    horizon_months: z.number().int(),
    projected_score: z.number(),
    narrative: z.string(),
    computed_at: z.string(),
  })
  .passthrough();

export type OutlookOut = z.infer<typeof OutlookOutSchema>;

export const OutlookNarratorResponseSchema = z
  .object({
    ai_meta: AIMetaSchema,
    narrative: z.string(),
    disclaimer: z.string().optional(),
  })
  .passthrough();

export type OutlookNarratorResponse = z.infer<
  typeof OutlookNarratorResponseSchema
>;

// ---------------------------------------------------------------------------
// Insights
// ---------------------------------------------------------------------------

export const InsightOutSchema = z
  .object({
    kind: z.string(),
    severity: z.enum(["low", "moderate", "high"]),
    message: z.string(),
    disclaimer: z.string().optional(),
    signals: z.array(z.string()).optional(),
    prevention_signals: z.array(z.string()).optional(),
  })
  .passthrough();

export type InsightOut = z.infer<typeof InsightOutSchema>;

export const InsightsListOutSchema = z
  .object({
    patient_id: z.string(),
    insights: z.array(InsightOutSchema).optional(),
    risk_flags: z.array(z.string()).optional(),
    signals: z.array(z.string()).optional(),
    prevention_signals: z.array(z.string()).optional(),
  })
  .passthrough();

export type InsightsListOut = z.infer<typeof InsightsListOutSchema>;

// ---------------------------------------------------------------------------
// Future Self
// ---------------------------------------------------------------------------

export const FutureSelfResponseSchema = z
  .object({
    ai_meta: AIMetaSchema,
    bio_age: z.number().int(),
    narrative: z.string(),
    disclaimer: z.string().optional(),
  })
  .passthrough();

export type FutureSelfResponse = z.infer<typeof FutureSelfResponseSchema>;

// ---------------------------------------------------------------------------
// Protocol
// ---------------------------------------------------------------------------

export const ProtocolActionOutSchema = z
  .object({
    id: z.number().int(),
    protocol_id: z.number().int(),
    category: z.string(),
    title: z.string(),
    completed_today: z.boolean().optional(),
    streak_days: z.number().int().optional(),
    dimension: z.string().nullish(),
    rationale: z.string().nullish(),
    target: z.string().nullish(),
    /** B3: ordering support */
    sort_order: z.number().int().nullish(),
    /** B3: skip-with-reason support */
    skipped_today: z.boolean().optional(),
    skip_reason: z.string().nullish(),
  })
  .passthrough();

export type ProtocolActionOut = z.infer<typeof ProtocolActionOutSchema>;

/**
 * Request body for skipping a protocol action with a reason (B3).
 * Hits POST /api/proxy/protocol/skip-action.
 */
export const ProtocolSkipInputSchema = z
  .object({
    action_id: z.number().int(),
    reason: z.string(),
  })
  .passthrough();

export type ProtocolSkipInput = z.infer<typeof ProtocolSkipInputSchema>;

/**
 * Request body for reordering protocol actions (B3).
 * Hits POST /api/proxy/protocol/reorder.
 */
export const ProtocolReorderInputSchema = z
  .object({
    action_ids: z.array(z.number().int()),
  })
  .passthrough();

export type ProtocolReorderInput = z.infer<typeof ProtocolReorderInputSchema>;

export const ProtocolOutSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    created_at: z.string(),
    actions: z.array(ProtocolActionOutSchema).optional(),
    rationale: z.string().nullish(),
  })
  .passthrough();

export type ProtocolOut = z.infer<typeof ProtocolOutSchema>;

export const CompleteActionResponseSchema = z
  .object({
    action_id: z.number().int(),
    streak_days: z.number().int(),
    completed_at: z.string(),
  })
  .passthrough();

export type CompleteActionResponse = z.infer<typeof CompleteActionResponseSchema>;

// ---------------------------------------------------------------------------
// Daily Log
// ---------------------------------------------------------------------------

export const DailyLogOutSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    date: z.string(),
    logged_at: z.string(),
    mood_score: z.number().int().nullish(),
    sleep_hours: z.number().nullish(),
    workout_minutes: z.number().int().nullish(),
    water_glasses: z.number().int().nullish(),
    alcohol_units: z.number().int().nullish(),
    /** B1: structured sleep quality (1–5) */
    sleep_quality: z.number().int().min(1).max(5).nullish(),
    /** B1: workout type (walk|run|bike|strength|yoga|other) */
    workout_type: z.string().nullish(),
    /** B1: workout intensity (low|med|high) */
    workout_intensity: z.string().nullish(),
    /** B4: water intake in millilitres */
    water_ml: z.number().int().nullish(),
  })
  .passthrough();

export type DailyLogOut = z.infer<typeof DailyLogOutSchema>;

/**
 * Input shape for creating a daily log entry (B4).
 * All fields except `date` are optional.
 */
export const DailyLogCreateInputSchema = z
  .object({
    date: z.string(),
    mood_score: z.number().int().nullish(),
    sleep_hours: z.number().nullish(),
    sleep_quality: z.number().int().min(1).max(5).nullish(),
    workout_minutes: z.number().int().nullish(),
    workout_type: z.string().nullish(),
    workout_intensity: z.string().nullish(),
    water_glasses: z.number().int().nullish(),
    water_ml: z.number().int().nullish(),
    alcohol_units: z.number().int().nullish(),
  })
  .passthrough();

export type DailyLogCreateInput = z.infer<typeof DailyLogCreateInputSchema>;

export const DailyLogListOutSchema = z
  .object({
    patient_id: z.string(),
    logs: z.array(DailyLogOutSchema).optional(),
  })
  .passthrough();

export type DailyLogListOut = z.infer<typeof DailyLogListOutSchema>;

// ---------------------------------------------------------------------------
// Meal Log
// ---------------------------------------------------------------------------

export const MealAnalysisSchema = z
  .object({
    classification: z.string(),
    macros: z.record(z.unknown()),
    longevity_swap: z.string(),
    swap_rationale: z.string(),
  })
  .passthrough();

export type MealAnalysis = z.infer<typeof MealAnalysisSchema>;

export const MealLogOutSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    logged_at: z.string(),
    /**
     * May be null for manual entries that haven't been assigned a URI yet,
     * or a `manual://<uuid>` sentinel for B2 manual meal logs.
     */
    photo_uri: z.string().nullish(),
    analysis: MealAnalysisSchema,
    notes: z.string().nullish(),
  })
  .passthrough();

export type MealLogOut = z.infer<typeof MealLogOutSchema>;

/**
 * Input shape for manually logging a meal without a photo (B2/B4).
 * Hits POST /api/proxy/meal-log/manual.
 */
export const ManualMealLogInputSchema = z
  .object({
    name: z.string(),
    kcal: z.number(),
    protein_g: z.number(),
    carbs_g: z.number(),
    fat_g: z.number(),
    fiber_g: z.number(),
    notes: z.string().optional(),
  })
  .passthrough();

export type ManualMealLogInput = z.infer<typeof ManualMealLogInputSchema>;

export const MealLogListOutSchema = z
  .object({
    patient_id: z.string(),
    logs: z.array(MealLogOutSchema).optional(),
  })
  .passthrough();

export type MealLogListOut = z.infer<typeof MealLogListOutSchema>;

export const MealLogUploadResponseSchema = z
  .object({
    ai_meta: AIMetaSchema,
    meal_log_id: z.number().int(),
    /** May be a `manual://<uuid>` sentinel for B2 manual meal log entries. */
    photo_uri: z.string().nullish(),
    analysis: MealAnalysisSchema,
    disclaimer: z.string().optional(),
  })
  .passthrough();

export type MealLogUploadResponse = z.infer<typeof MealLogUploadResponseSchema>;

// ---------------------------------------------------------------------------
// Coach / Chat SSE
// ---------------------------------------------------------------------------

/**
 * A single SSE chunk from the coach/chat stream.
 * event: "token" carries a text delta; "done" carries ai_meta; "error" carries an error message.
 */
export const ChatChunkSchema = z
  .object({
    event: z.enum(["token", "done", "error"]),
    data: z.string(),
  })
  .passthrough();

export type ChatChunk = z.infer<typeof ChatChunkSchema>;

// ---------------------------------------------------------------------------
// EHR Records
// ---------------------------------------------------------------------------

export const EHRRecordOutSchema = z
  .object({
    id: z.number().int(),
    record_type: z.string(),
    recorded_at: z.string(),
    payload: z.record(z.unknown()),
    source: z.string(),
  })
  .passthrough();

export type EHRRecordOut = z.infer<typeof EHRRecordOutSchema>;

export const EHRRecordListOutSchema = z
  .object({
    patient_id: z.string(),
    total: z.number().int(),
    records: z.array(EHRRecordOutSchema).optional(),
  })
  .passthrough();

export type EHRRecordListOut = z.infer<typeof EHRRecordListOutSchema>;

export const CitationSchema = z
  .object({
    record_id: z.number().int(),
    snippet: z.string(),
  })
  .passthrough();

export type Citation = z.infer<typeof CitationSchema>;

export const RecordsQAResponseSchema = z
  .object({
    ai_meta: AIMetaSchema,
    answer: z.string(),
    citations: z.array(CitationSchema).optional(),
    disclaimer: z.string().optional(),
  })
  .passthrough();

export type RecordsQAResponse = z.infer<typeof RecordsQAResponseSchema>;

// ---------------------------------------------------------------------------
// Survey
// ---------------------------------------------------------------------------

export const SurveyKindSchema = z.enum(["onboarding", "weekly", "quarterly"]);
export type SurveyKind = z.infer<typeof SurveyKindSchema>;

export const SurveyResponseOutSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    kind: SurveyKindSchema,
    submitted_at: z.string(),
    answers: z.record(z.unknown()).optional(),
  })
  .passthrough();

export type SurveyResponseOut = z.infer<typeof SurveyResponseOutSchema>;

export const SurveyHistoryOutSchema = z
  .object({
    patient_id: z.string(),
    responses: z.array(SurveyResponseOutSchema).optional(),
  })
  .passthrough();

export type SurveyHistoryOut = z.infer<typeof SurveyHistoryOutSchema>;

// ---------------------------------------------------------------------------
// Appointments
// ---------------------------------------------------------------------------

export const AppointmentOutSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    provider: z.string(),
    location: z.string(),
    starts_at: z.string(),
    duration_minutes: z.number().int(),
    price_eur: z.number().nullish(),
    covered_percent: z.number().int().nullish(),
  })
  .passthrough();

export type AppointmentOut = z.infer<typeof AppointmentOutSchema>;

export const AppointmentListOutSchema = z
  .object({
    patient_id: z.string(),
    appointments: z.array(AppointmentOutSchema).optional(),
  })
  .passthrough();

export type AppointmentListOut = z.infer<typeof AppointmentListOutSchema>;

// ---------------------------------------------------------------------------
// Clinical Review
// ---------------------------------------------------------------------------

export const ClinicalReviewResponseSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    notes: z.string(),
    reason: z.string(),
    status: z.string(),
    created_at: z.string(),
  })
  .passthrough();

export type ClinicalReviewResponse = z.infer<typeof ClinicalReviewResponseSchema>;

// ---------------------------------------------------------------------------
// Referral
// ---------------------------------------------------------------------------

export const ReferralResponseSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    code: z.string(),
    specialty: z.string(),
    reason: z.string(),
    status: z.string(),
    created_at: z.string(),
  })
  .passthrough();

export type ReferralResponse = z.infer<typeof ReferralResponseSchema>;

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export const MessageOutSchema = z
  .object({
    id: z.number().int(),
    patient_id: z.string(),
    content: z.string(),
    sent_at: z.string(),
    direction: z.enum(["inbound", "outbound"]),
  })
  .passthrough();

export type MessageOut = z.infer<typeof MessageOutSchema>;

export const MessageListOutSchema = z
  .object({
    patient_id: z.string(),
    messages: z.array(MessageOutSchema).optional(),
  })
  .passthrough();

export type MessageListOut = z.infer<typeof MessageListOutSchema>;

// ---------------------------------------------------------------------------
// Smart Notifications
// ---------------------------------------------------------------------------

export const SmartNotificationResponseSchema = z
  .object({
    ai_meta: AIMetaSchema,
    title: z.string(),
    body: z.string(),
    cta: z.string(),
    disclaimer: z.string().optional(),
  })
  .passthrough();

export type SmartNotificationResponse = z.infer<
  typeof SmartNotificationResponseSchema
>;

// ---------------------------------------------------------------------------
// GDPR
// ---------------------------------------------------------------------------

export const GDPRExportOutSchema = z
  .object({
    patient_id: z.string(),
    patient: PatientProfileOutSchema,
    exported_at: z.string().optional(),
    records: z.array(EHRRecordOutSchema).optional(),
    wearable: z.array(WearableDayOutSchema).optional(),
    lifestyle: z.unknown().optional(),
  })
  .passthrough();

export type GDPRExportOut = z.infer<typeof GDPRExportOutSchema>;

export const GDPRDeleteAckSchema = z
  .object({
    message: z.string(),
    status: z.literal("scheduled").optional(),
  })
  .passthrough();

export type GDPRDeleteAck = z.infer<typeof GDPRDeleteAckSchema>;
