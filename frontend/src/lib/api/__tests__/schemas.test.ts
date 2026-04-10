/**
 * Unit tests for Zod schema validation.
 *
 * Tests valid fixtures (should parse) and invalid fixtures (should fail).
 * Uses passthrough mode — extra fields are allowed.
 */

import { describe, it, expect } from "vitest";
import {
  AIMetaSchema,
  PatientProfileOutSchema,
  VitalityOutSchema,
  WearableSeriesOutSchema,
  OutlookOutSchema,
  OutlookNarratorResponseSchema,
  InsightsListOutSchema,
  InsightOutSchema,
  FutureSelfResponseSchema,
  ProtocolOutSchema,
  CompleteActionResponseSchema,
  DailyLogListOutSchema,
  DailyLogOutSchema,
  MealLogListOutSchema,
  MealLogUploadResponseSchema,
  ChatChunkSchema,
  EHRRecordListOutSchema,
  RecordsQAResponseSchema,
  SurveyHistoryOutSchema,
  SurveyResponseOutSchema,
  AppointmentListOutSchema,
  AppointmentOutSchema,
  ClinicalReviewResponseSchema,
  ReferralResponseSchema,
  MessageListOutSchema,
  MessageOutSchema,
  SmartNotificationResponseSchema,
  GDPRExportOutSchema,
  GDPRDeleteAckSchema,
} from "../schemas";

// ---------------------------------------------------------------------------
// AIMeta
// ---------------------------------------------------------------------------

describe("AIMetaSchema", () => {
  const validAIMeta = {
    model: "gemini-2.5-flash",
    prompt_name: "coach",
    request_id: "req-abc123",
    token_in: 100,
    token_out: 50,
    latency_ms: 1200,
  };

  it("parses a valid AIMeta", () => {
    expect(AIMetaSchema.parse(validAIMeta)).toMatchObject(validAIMeta);
  });

  it("fails when model is missing", () => {
    const withoutModel = { ...validAIMeta, model: undefined };
    expect(() => AIMetaSchema.parse(withoutModel)).toThrow();
  });

  it("allows extra fields (passthrough)", () => {
    const withExtra = { ...validAIMeta, extra_field: "ignored" };
    const result = AIMetaSchema.parse(withExtra);
    expect((result as Record<string, unknown>).extra_field).toBe("ignored");
  });
});

// ---------------------------------------------------------------------------
// PatientProfileOut
// ---------------------------------------------------------------------------

describe("PatientProfileOutSchema", () => {
  const valid = {
    patient_id: "PT0199",
    name: "Rebecca Müller",
    age: 38,
    country: "Germany",
  };

  it("parses a minimal valid profile", () => {
    expect(PatientProfileOutSchema.parse(valid)).toMatchObject(valid);
  });

  it("parses a full profile with optional fields", () => {
    const full = {
      ...valid,
      sex: "female",
      bmi: 22.5,
      height_cm: 168.0,
      weight_kg: 63.5,
      smoking_status: "never",
    };
    expect(PatientProfileOutSchema.parse(full)).toMatchObject(full);
  });

  it("accepts null for optional fields", () => {
    const withNulls = { ...valid, sex: null, bmi: null };
    expect(PatientProfileOutSchema.parse(withNulls)).toMatchObject(withNulls);
  });

  it("fails when patient_id is missing", () => {
    const withoutId = { ...valid, patient_id: undefined };
    expect(() => PatientProfileOutSchema.parse(withoutId)).toThrow();
  });

  it("fails when age is not a number", () => {
    expect(() =>
      PatientProfileOutSchema.parse({ ...valid, age: "thirty-eight" }),
    ).toThrow();
  });
});

// ---------------------------------------------------------------------------
// VitalityOut
// ---------------------------------------------------------------------------

describe("VitalityOutSchema", () => {
  const valid = {
    score: 72.5,
    subscores: { sleep: 80, activity: 65, metabolic: 70 },
    computed_at: "2026-04-09T08:00:00",
  };

  it("parses a valid vitality response", () => {
    expect(VitalityOutSchema.parse(valid)).toMatchObject(valid);
  });

  it("parses with optional trend array", () => {
    const withTrend = {
      ...valid,
      trend: [
        { date: "2026-04-02", score: 68 },
        { date: "2026-04-03", score: 70 },
      ],
    };
    expect(VitalityOutSchema.parse(withTrend)).toMatchObject(withTrend);
  });

  it("fails when score is missing", () => {
    const withoutScore = { ...valid, score: undefined };
    expect(() => VitalityOutSchema.parse(withoutScore)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// WearableSeriesOut
// ---------------------------------------------------------------------------

describe("WearableSeriesOutSchema", () => {
  it("parses a minimal wearable series", () => {
    const data = { patient_id: "PT0199", days: [] };
    expect(WearableSeriesOutSchema.parse(data)).toMatchObject(data);
  });

  it("parses a day with all metrics", () => {
    const data = {
      patient_id: "PT0199",
      days: [
        {
          patient_id: "PT0199",
          date: "2026-04-08",
          steps: 8432,
          active_minutes: 42,
          resting_hr_bpm: 62.0,
          hrv_rmssd_ms: 45.2,
          sleep_duration_hrs: 7.5,
        },
      ],
    };
    expect(WearableSeriesOutSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// OutlookOut
// ---------------------------------------------------------------------------

describe("OutlookOutSchema", () => {
  const valid = {
    horizon_months: 6,
    projected_score: 78.0,
    narrative: "Hold your streak and your Outlook reaches 74 by October.",
    computed_at: "2026-04-09T08:00:00",
  };

  it("parses a valid outlook", () => {
    expect(OutlookOutSchema.parse(valid)).toMatchObject(valid);
  });

  it("fails when narrative is missing", () => {
    const withoutNarrative = { ...valid, narrative: undefined };
    expect(() => OutlookOutSchema.parse(withoutNarrative)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// OutlookNarratorResponse
// ---------------------------------------------------------------------------

describe("OutlookNarratorResponseSchema", () => {
  const validAIMeta = {
    model: "gemini-2.5-flash",
    prompt_name: "outlook",
    request_id: "req-1",
    token_in: 100,
    token_out: 50,
    latency_ms: 1000,
  };

  it("parses a valid narrator response", () => {
    const data = {
      ai_meta: validAIMeta,
      narrative: "Keep it up.",
    };
    expect(OutlookNarratorResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// InsightsListOut
// ---------------------------------------------------------------------------

describe("InsightsListOutSchema", () => {
  it("parses a minimal insights list", () => {
    const data = { patient_id: "PT0199" };
    expect(InsightsListOutSchema.parse(data)).toMatchObject(data);
  });

  it("parses insights with items", () => {
    const data = {
      patient_id: "PT0199",
      insights: [
        {
          kind: "lipid",
          severity: "moderate" as const,
          message: "Your LDL trend suggests a wellness review.",
        },
      ],
    };
    expect(InsightsListOutSchema.parse(data)).toMatchObject(data);
  });

  it("rejects invalid severity", () => {
    const data = {
      patient_id: "PT0199",
      insights: [
        { kind: "lipid", severity: "critical", message: "Bad" },
      ],
    };
    expect(() => InsightsListOutSchema.parse(data)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// InsightOut
// ---------------------------------------------------------------------------

describe("InsightOutSchema", () => {
  it("fails with invalid severity", () => {
    const data = { kind: "sleep", severity: "extreme", message: "x" };
    expect(() => InsightOutSchema.parse(data)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// FutureSelfResponse
// ---------------------------------------------------------------------------

describe("FutureSelfResponseSchema", () => {
  const validAIMeta = {
    model: "gemini-2.5-flash",
    prompt_name: "future_self",
    request_id: "req-2",
    token_in: 200,
    token_out: 80,
    latency_ms: 1500,
  };

  it("parses a valid future self response", () => {
    const data = {
      ai_meta: validAIMeta,
      bio_age: 34,
      narrative: "Here's you at 70 on current trajectory vs improved.",
    };
    expect(FutureSelfResponseSchema.parse(data)).toMatchObject(data);
  });

  it("fails when bio_age is missing", () => {
    const data = {
      ai_meta: validAIMeta,
      narrative: "Narrative",
    };
    expect(() => FutureSelfResponseSchema.parse(data)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// ProtocolOut
// ---------------------------------------------------------------------------

describe("ProtocolOutSchema", () => {
  it("parses a valid protocol with actions", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      created_at: "2026-04-09T08:00:00",
      actions: [
        {
          id: 10,
          protocol_id: 1,
          category: "sleep",
          title: "Go to bed by 22:30",
          streak_days: 3,
          completed_today: false,
        },
      ],
    };
    expect(ProtocolOutSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// CompleteActionResponse
// ---------------------------------------------------------------------------

describe("CompleteActionResponseSchema", () => {
  it("parses a valid complete-action response", () => {
    const data = {
      action_id: 10,
      streak_days: 4,
      completed_at: "2026-04-09T09:00:00",
    };
    expect(CompleteActionResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// DailyLogListOut / DailyLogOut
// ---------------------------------------------------------------------------

describe("DailyLogListOutSchema", () => {
  it("parses an empty list", () => {
    const data = { patient_id: "PT0199", logs: [] };
    expect(DailyLogListOutSchema.parse(data)).toMatchObject(data);
  });
});

describe("DailyLogOutSchema", () => {
  it("parses a full log entry", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      date: "2026-04-09",
      logged_at: "2026-04-09T08:30:00",
      mood_score: 8,
      sleep_hours: 7.5,
      workout_minutes: 30,
      water_glasses: 8,
      alcohol_units: 0,
    };
    expect(DailyLogOutSchema.parse(data)).toMatchObject(data);
  });

  it("fails when date is missing", () => {
    const data = { id: 1, patient_id: "PT0199", logged_at: "2026-04-09T08:30:00" };
    expect(() => DailyLogOutSchema.parse(data)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// MealLogListOut / MealLogUploadResponse
// ---------------------------------------------------------------------------

describe("MealLogListOutSchema", () => {
  it("parses a meal log list", () => {
    const data = { patient_id: "PT0199", logs: [] };
    expect(MealLogListOutSchema.parse(data)).toMatchObject(data);
  });
});

describe("MealLogUploadResponseSchema", () => {
  const validAIMeta = {
    model: "gemini-2.5-flash",
    prompt_name: "meal_vision",
    request_id: "req-3",
    token_in: 150,
    token_out: 60,
    latency_ms: 800,
  };

  it("parses a valid upload response", () => {
    const data = {
      ai_meta: validAIMeta,
      meal_log_id: 5,
      photo_uri: "local://meals/abc.jpg",
      analysis: {
        classification: "grilled salmon, white rice, broccoli",
        macros: { kcal: 450, protein_g: 35.0, carbs_g: 40.0, fat_g: 12.0 },
        longevity_swap: "Replace white rice with quinoa.",
        swap_rationale: "Quinoa provides more protein and fibre.",
      },
    };
    expect(MealLogUploadResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// ChatChunk
// ---------------------------------------------------------------------------

describe("ChatChunkSchema", () => {
  it("parses a token chunk", () => {
    expect(ChatChunkSchema.parse({ event: "token", data: "Hello" })).toMatchObject({
      event: "token",
      data: "Hello",
    });
  });

  it("parses a done chunk", () => {
    expect(ChatChunkSchema.parse({ event: "done", data: "{}" })).toMatchObject({
      event: "done",
    });
  });

  it("parses an error chunk", () => {
    expect(ChatChunkSchema.parse({ event: "error", data: "oops" })).toMatchObject({
      event: "error",
    });
  });

  it("fails for unknown event types", () => {
    expect(() =>
      ChatChunkSchema.parse({ event: "unknown", data: "x" }),
    ).toThrow();
  });
});

// ---------------------------------------------------------------------------
// EHRRecordListOut / RecordsQAResponse
// ---------------------------------------------------------------------------

describe("EHRRecordListOutSchema", () => {
  it("parses a valid record list", () => {
    const data = {
      patient_id: "PT0199",
      total: 0,
      records: [],
    };
    expect(EHRRecordListOutSchema.parse(data)).toMatchObject(data);
  });
});

describe("RecordsQAResponseSchema", () => {
  const validAIMeta = {
    model: "gemini-2.5-flash",
    prompt_name: "records_qa",
    request_id: "req-4",
    token_in: 300,
    token_out: 100,
    latency_ms: 2000,
  };

  it("parses a valid QA response", () => {
    const data = {
      ai_meta: validAIMeta,
      answer: "Your last LDL reading was 135 mg/dL.",
      citations: [{ record_id: 42, snippet: "LDL: 135 mg/dL" }],
    };
    expect(RecordsQAResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// SurveyHistoryOut
// ---------------------------------------------------------------------------

describe("SurveyHistoryOutSchema", () => {
  it("parses an empty survey history", () => {
    const data = { patient_id: "PT0199", responses: [] };
    expect(SurveyHistoryOutSchema.parse(data)).toMatchObject(data);
  });

  it("rejects invalid survey kind", () => {
    const data = {
      patient_id: "PT0199",
      responses: [
        {
          id: 1,
          patient_id: "PT0199",
          kind: "annual",
          submitted_at: "2026-04-01T00:00:00",
        },
      ],
    };
    expect(() => SurveyHistoryOutSchema.parse(data)).toThrow();
  });
});

describe("SurveyResponseOutSchema", () => {
  it("parses a valid survey response", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      kind: "onboarding" as const,
      submitted_at: "2026-04-01T00:00:00",
      answers: { sleep_goal: 8 },
    };
    expect(SurveyResponseOutSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// AppointmentListOut / AppointmentOut
// ---------------------------------------------------------------------------

describe("AppointmentListOutSchema", () => {
  it("parses a valid appointment list", () => {
    const data = { patient_id: "PT0199", appointments: [] };
    expect(AppointmentListOutSchema.parse(data)).toMatchObject(data);
  });
});

describe("AppointmentOutSchema", () => {
  it("parses a valid appointment", () => {
    const data = {
      id: "apt-1",
      title: "Longevity Assessment",
      provider: "Dr. Müller",
      location: "Hamburg Clinic",
      starts_at: "2026-05-01T09:00:00",
      duration_minutes: 60,
    };
    expect(AppointmentOutSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// ClinicalReviewResponse
// ---------------------------------------------------------------------------

describe("ClinicalReviewResponseSchema", () => {
  it("parses a valid clinical review", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      notes: "Elevated LDL trend",
      reason: "Elevated LDL trend",
      status: "pending",
      created_at: "2026-04-09T08:00:00",
    };
    expect(ClinicalReviewResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// ReferralResponse
// ---------------------------------------------------------------------------

describe("ReferralResponseSchema", () => {
  it("parses a valid referral", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      code: "REF-ABC123",
      specialty: "cardiology",
      reason: "Routine cardiac wellness screening",
      status: "pending",
      created_at: "2026-04-09T08:00:00",
    };
    expect(ReferralResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// MessageListOut / MessageOut
// ---------------------------------------------------------------------------

describe("MessageListOutSchema", () => {
  it("parses a valid message list", () => {
    const data = { patient_id: "PT0199", messages: [] };
    expect(MessageListOutSchema.parse(data)).toMatchObject(data);
  });
});

describe("MessageOutSchema", () => {
  it("parses an inbound message", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      content: "How are my vitals?",
      sent_at: "2026-04-09T10:00:00",
      direction: "inbound" as const,
    };
    expect(MessageOutSchema.parse(data)).toMatchObject(data);
  });

  it("fails for unknown direction", () => {
    const data = {
      id: 1,
      patient_id: "PT0199",
      content: "x",
      sent_at: "2026-04-09T10:00:00",
      direction: "both",
    };
    expect(() => MessageOutSchema.parse(data)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// SmartNotificationResponse
// ---------------------------------------------------------------------------

describe("SmartNotificationResponseSchema", () => {
  const validAIMeta = {
    model: "gemini-2.5-flash",
    prompt_name: "notification",
    request_id: "req-5",
    token_in: 80,
    token_out: 40,
    latency_ms: 600,
  };

  it("parses a valid notification response", () => {
    const data = {
      ai_meta: validAIMeta,
      title: "Keep your streak alive!",
      body: "You've been consistent this week — one more day to lock in your 7-day streak.",
      cta: "Log activity",
    };
    expect(SmartNotificationResponseSchema.parse(data)).toMatchObject(data);
  });
});

// ---------------------------------------------------------------------------
// GDPRExportOut / GDPRDeleteAck
// ---------------------------------------------------------------------------

describe("GDPRExportOutSchema", () => {
  it("parses a minimal GDPR export", () => {
    const data = {
      patient_id: "PT0199",
      patient: {
        patient_id: "PT0199",
        name: "Rebecca Müller",
        age: 38,
        country: "Germany",
      },
    };
    expect(GDPRExportOutSchema.parse(data)).toMatchObject(data);
  });
});

describe("GDPRDeleteAckSchema", () => {
  it("parses a valid delete ack", () => {
    const data = {
      message: "Your erasure request has been scheduled.",
      status: "scheduled",
    };
    expect(GDPRDeleteAckSchema.parse(data)).toMatchObject(data);
  });

  it("parses without optional status", () => {
    const data = { message: "Scheduled." };
    expect(GDPRDeleteAckSchema.parse(data)).toMatchObject(data);
  });
});
