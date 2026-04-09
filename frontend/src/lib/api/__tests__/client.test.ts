/**
 * Unit tests for the API client.
 *
 * Uses vi.fn() to mock global fetch so tests remain fast and isolated
 * (no network or server required).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getPatientProfile,
  getVitality,
  getWearable,
  getOutlook,
  getInsights,
  getProtocol,
  getDailyLogs,
  getRecords,
  getSurveyHistory,
  getAppointments,
  getMessages,
  getGDPRExport,
  createDailyLog,
  completeProtocolAction,
  postRecordsQA,
  submitSurvey,
  bookAppointment,
  createClinicalReview,
  createReferral,
  sendMessage,
  createSmartNotification,
  requestGDPRDelete,
  postOutlookNarrator,
  postFutureSelf,
  generateProtocol,
} from "../client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Create a minimal Response-like mock with json() helper. */
function mockResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as unknown as Response;
}

/** Create a fetch mock that returns a canned response. */
function mockFetch(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue(mockResponse(body, status));
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// GET endpoints
// ---------------------------------------------------------------------------

describe("getPatientProfile", () => {
  it("calls /api/proxy/profile and returns the body", async () => {
    const profile = {
      patient_id: "PT0199",
      name: "Rebecca",
      age: 38,
      country: "Germany",
    };
    vi.stubGlobal("fetch", mockFetch(profile));

    const result = await getPatientProfile();
    expect(result).toEqual(profile);

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/profile");
  });
});

describe("getVitality", () => {
  it("calls /api/proxy/vitality", async () => {
    const vitality = { score: 72, subscores: {}, computed_at: "2026-04-09T08:00:00" };
    vi.stubGlobal("fetch", mockFetch(vitality));

    const result = await getVitality();
    expect(result.score).toBe(72);

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/vitality");
  });
});

describe("getWearable", () => {
  it("calls /api/proxy/wearable", async () => {
    const wearable = { patient_id: "PT0199", days: [] };
    vi.stubGlobal("fetch", mockFetch(wearable));

    await getWearable();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/wearable");
  });
});

describe("getOutlook", () => {
  it("calls /api/proxy/outlook", async () => {
    const outlook = {
      horizon_months: 6,
      projected_score: 78,
      narrative: "Great trajectory.",
      computed_at: "2026-04-09T08:00:00",
    };
    vi.stubGlobal("fetch", mockFetch(outlook));

    await getOutlook();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/outlook");
  });
});

describe("getInsights", () => {
  it("calls /api/proxy/insights", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199" }));
    await getInsights();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/insights");
  });
});

describe("getProtocol", () => {
  it("calls /api/proxy/protocol", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ id: 1, patient_id: "PT0199", created_at: "2026-04-09T08:00:00" }),
    );
    await getProtocol();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/protocol");
  });
});

describe("getDailyLogs", () => {
  it("calls /api/proxy/daily-log with from/to query params", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199", logs: [] }));
    await getDailyLogs({ from: "2026-04-01", to: "2026-04-09" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toContain("/api/proxy/daily-log");
    expect(url).toContain("from=2026-04-01");
    expect(url).toContain("to=2026-04-09");
  });
});

describe("getRecords", () => {
  it("calls /api/proxy/records", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199", total: 0 }));
    await getRecords();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/records");
  });

  it("appends limit/offset/record_type query params", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199", total: 0 }));
    await getRecords({ limit: 10, offset: 20, record_type: "lab_panel" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toContain("limit=10");
    expect(url).toContain("offset=20");
    expect(url).toContain("record_type=lab_panel");
  });
});

describe("getSurveyHistory", () => {
  it("calls /api/proxy/survey", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199" }));
    await getSurveyHistory();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/survey");
  });
});

describe("getAppointments", () => {
  it("calls /api/proxy/appointments/", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199" }));
    await getAppointments();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/appointments/");
  });
});

describe("getMessages", () => {
  it("calls /api/proxy/messages", async () => {
    vi.stubGlobal("fetch", mockFetch({ patient_id: "PT0199" }));
    await getMessages();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/messages");
  });
});

describe("getGDPRExport", () => {
  it("calls /api/proxy/gdpr/export", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        patient_id: "PT0199",
        patient: { patient_id: "PT0199", name: "Rebecca", age: 38, country: "Germany" },
      }),
    );
    await getGDPRExport();
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/gdpr/export");
  });
});

// ---------------------------------------------------------------------------
// POST / mutation endpoints
// ---------------------------------------------------------------------------

describe("createDailyLog", () => {
  it("POSTs to /api/proxy/daily-log with the body", async () => {
    const logOut = {
      id: 1,
      patient_id: "PT0199",
      date: "2026-04-09",
      logged_at: "2026-04-09T08:00:00",
    };
    vi.stubGlobal("fetch", mockFetch(logOut));

    const result = await createDailyLog({ date: "2026-04-09", mood_score: 8 });
    expect(result.id).toBe(1);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(call[0]).toBe("/api/proxy/daily-log");
    expect(call[1].method).toBe("POST");

    const parsedBody = JSON.parse(call[1].body as string) as Record<string, unknown>;
    expect(parsedBody.date).toBe("2026-04-09");
    expect(parsedBody.mood_score).toBe(8);
  });
});

describe("completeProtocolAction", () => {
  it("POSTs to /api/proxy/protocol/complete-action", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ action_id: 10, streak_days: 4, completed_at: "2026-04-09T09:00:00" }),
    );

    await completeProtocolAction(10);

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(call[0]).toBe("/api/proxy/protocol/complete-action");
    expect(call[1].method).toBe("POST");
    const body = JSON.parse(call[1].body as string) as { action_id: number };
    expect(body.action_id).toBe(10);
  });
});

describe("postRecordsQA", () => {
  it("POSTs to /api/proxy/records/qa", async () => {
    const validAIMeta = {
      model: "gemini-2.5-flash",
      prompt_name: "records_qa",
      request_id: "req-4",
      token_in: 300,
      token_out: 100,
      latency_ms: 2000,
    };
    vi.stubGlobal(
      "fetch",
      mockFetch({ ai_meta: validAIMeta, answer: "Your LDL was 135." }),
    );

    const result = await postRecordsQA("What was my last LDL?");
    expect(result.answer).toBe("Your LDL was 135.");

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/records/qa");
  });
});

describe("submitSurvey", () => {
  it("POSTs to /api/proxy/survey", async () => {
    const response = {
      id: 1,
      patient_id: "PT0199",
      kind: "weekly",
      submitted_at: "2026-04-09T08:00:00",
    };
    vi.stubGlobal("fetch", mockFetch(response));

    await submitSurvey({ kind: "weekly", answers: { sleep: 8 } });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/survey");
  });
});

describe("bookAppointment", () => {
  it("POSTs to /api/proxy/appointments/", async () => {
    const apt = {
      id: "apt-1",
      title: "Assessment",
      provider: "Dr. S",
      location: "Hamburg",
      starts_at: "2026-05-01T09:00:00",
      duration_minutes: 60,
    };
    vi.stubGlobal("fetch", mockFetch(apt, 201));

    await bookAppointment({
      title: "Assessment",
      provider: "Dr. S",
      location: "Hamburg",
      starts_at: "2026-05-01T09:00:00",
      duration_minutes: 60,
    });

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/appointments/");
  });
});

describe("createClinicalReview", () => {
  it("POSTs to /api/proxy/clinical-review", async () => {
    const review = {
      id: 1,
      patient_id: "PT0199",
      notes: "Elevated LDL",
      reason: "Elevated LDL",
      status: "pending",
      created_at: "2026-04-09T08:00:00",
    };
    vi.stubGlobal("fetch", mockFetch(review));
    await createClinicalReview({ patient_id: "PT0199", notes: "Elevated LDL" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/clinical-review");
  });
});

describe("createReferral", () => {
  it("POSTs to /api/proxy/referral", async () => {
    const referral = {
      id: 1,
      patient_id: "PT0199",
      code: "REF-1",
      specialty: "cardiology",
      reason: "Routine",
      status: "pending",
      created_at: "2026-04-09T08:00:00",
    };
    vi.stubGlobal("fetch", mockFetch(referral));
    await createReferral({ patient_id: "PT0199", specialty: "cardiology", reason: "Routine" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/referral");
  });
});

describe("sendMessage", () => {
  it("POSTs to /api/proxy/messages", async () => {
    const msg = {
      id: 1,
      patient_id: "PT0199",
      content: "Hello",
      sent_at: "2026-04-09T10:00:00",
      direction: "inbound",
    };
    vi.stubGlobal("fetch", mockFetch(msg));
    await sendMessage({ patient_id: "PT0199", content: "Hello" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/messages");
  });
});

describe("createSmartNotification", () => {
  it("POSTs to /api/proxy/notifications/smart", async () => {
    const validAIMeta = {
      model: "gemini-2.5-flash",
      prompt_name: "notification",
      request_id: "req-5",
      token_in: 80,
      token_out: 40,
      latency_ms: 600,
    };
    const notif = {
      ai_meta: validAIMeta,
      title: "Keep up!",
      body: "You're on a streak.",
      cta: "Log activity",
    };
    vi.stubGlobal("fetch", mockFetch(notif));
    await createSmartNotification({ trigger_kind: "streak_at_risk" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/notifications/smart");
  });
});

describe("requestGDPRDelete", () => {
  it("DELETEs /api/proxy/gdpr", async () => {
    vi.stubGlobal("fetch", mockFetch({ message: "Scheduled.", status: "scheduled" }));
    await requestGDPRDelete();
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(call[0]).toBe("/api/proxy/gdpr");
    expect(call[1].method).toBe("DELETE");
  });
});

describe("postOutlookNarrator", () => {
  it("POSTs to /api/proxy/outlook-narrator", async () => {
    const validAIMeta = {
      model: "gemini-2.5-flash",
      prompt_name: "outlook",
      request_id: "req-1",
      token_in: 100,
      token_out: 50,
      latency_ms: 1000,
    };
    vi.stubGlobal("fetch", mockFetch({ ai_meta: validAIMeta, narrative: "Keep it up." }));
    await postOutlookNarrator({ patient_id: "PT0199" });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/outlook-narrator");
  });
});

describe("postFutureSelf", () => {
  it("POSTs to /api/proxy/future-self", async () => {
    const validAIMeta = {
      model: "gemini-2.5-flash",
      prompt_name: "future_self",
      request_id: "req-2",
      token_in: 200,
      token_out: 80,
      latency_ms: 1500,
    };
    vi.stubGlobal(
      "fetch",
      mockFetch({ ai_meta: validAIMeta, bio_age: 34, narrative: "Narrative." }),
    );
    await postFutureSelf({ patient_id: "PT0199", sliders: { sleep_improvement: 2 } });
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/proxy/future-self");
  });
});

describe("generateProtocol", () => {
  it("POSTs to /api/proxy/protocol/generate", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ id: 2, patient_id: "PT0199", created_at: "2026-04-09T08:00:00" }),
    );
    await generateProtocol();
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(call[0]).toBe("/api/proxy/protocol/generate");
    expect(call[1].method).toBe("POST");
  });
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe("error handling", () => {
  it("throws on non-2xx response", async () => {
    vi.stubGlobal("fetch", mockFetch({ error: "Not found" }, 404));
    await expect(getPatientProfile()).rejects.toThrow("API error 404");
  });

  it("throws on 401", async () => {
    vi.stubGlobal("fetch", mockFetch({ error: "Unauthorized" }, 401));
    await expect(getVitality()).rejects.toThrow("API error 401");
  });
});
