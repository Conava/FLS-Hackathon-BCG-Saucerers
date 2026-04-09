/**
 * Unit tests for RecentlyCard.
 *
 * The component is a pure server-renderable function — no hooks, no client
 * state — so it can be rendered directly with @testing-library/react.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecentlyCard } from "../_components/RecentlyCard";
import type { EHRRecordOut, VitalityOut } from "@/lib/api/schemas";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const LAB_RECORD: EHRRecordOut = {
  id: 1,
  record_type: "lab_panel",
  recorded_at: "2025-11-15T10:00:00Z",
  source: "csv",
  payload: {
    total_cholesterol_mmol: 5.8,
    ldl_mmol: 3.8, // > 3.4 — should trigger warn chip
    hdl_mmol: 1.3,
    triglycerides_mmol: 1.5,
    hba1c_pct: 5.4,
    fasting_glucose_mmol: 5.1,
    crp_mg_l: 1.2,
    egfr_ml_min: 85,
    sbp_mmhg: 122,
    dbp_mmhg: 78,
  },
};

const VITALITY_WITH_TREND: VitalityOut = {
  score: 71,
  subscores: { cardio: 70, metabolic: 72, sleep: 68, activity: 74, lifestyle: 71 },
  computed_at: "2026-04-09T08:00:00Z",
  risk_flags: [],
  trend: [
    { date: "2026-04-07", score: 68 },
    { date: "2026-04-08", score: 71 },
  ],
};

const VITALITY_FLAT: VitalityOut = {
  score: 70,
  subscores: { cardio: 70, metabolic: 70, sleep: 70, activity: 70, lifestyle: 70 },
  computed_at: "2026-04-09T08:00:00Z",
  risk_flags: [],
  trend: [
    { date: "2026-04-07", score: 70 },
    { date: "2026-04-08", score: 70 },
  ],
};

const VITALITY_DOWN: VitalityOut = {
  score: 68,
  subscores: { cardio: 68, metabolic: 68, sleep: 68, activity: 68, lifestyle: 68 },
  computed_at: "2026-04-09T08:00:00Z",
  risk_flags: [],
  trend: [
    { date: "2026-04-07", score: 72 },
    { date: "2026-04-08", score: 68 },
  ],
};

const VITALITY_NO_TREND: VitalityOut = {
  score: 71,
  subscores: { cardio: 70, metabolic: 72, sleep: 68, activity: 74, lifestyle: 71 },
  computed_at: "2026-04-09T08:00:00Z",
  risk_flags: [],
  trend: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("RecentlyCard", () => {
  // ── Lab row ─────────────────────────────────────────────────────────────────

  it("renders the lab title when lab record is present", () => {
    render(<RecentlyCard latestLab={LAB_RECORD} vitality={null} />);
    expect(screen.getByText("Lipid panel")).toBeInTheDocument();
  });

  it("shows a warn chip when LDL is elevated", () => {
    render(<RecentlyCard latestLab={LAB_RECORD} vitality={null} />);
    // LDL 3.8 mmol/L > 3.4 threshold → warn chip
    expect(screen.getByText(/LDL 3\.8/)).toBeInTheDocument();
  });

  it("shows 'Reviewed' muted chip when no lab values are flagged", () => {
    const normalLab: EHRRecordOut = {
      ...LAB_RECORD,
      payload: {
        ldl_mmol: 2.5,
        total_cholesterol_mmol: 4.0,
        hba1c_pct: 5.0,
        fasting_glucose_mmol: 4.5,
        crp_mg_l: 0.8,
        triglycerides_mmol: 1.0,
        hdl_mmol: 1.5,
      },
    };
    render(<RecentlyCard latestLab={normalLab} vitality={null} />);
    expect(screen.getByText("Reviewed")).toBeInTheDocument();
  });

  it("renders the lab date as month-year", () => {
    render(<RecentlyCard latestLab={LAB_RECORD} vitality={null} />);
    // "2025-11-15" → "Nov 2025"
    expect(screen.getByText(/Nov 2025/)).toBeInTheDocument();
  });

  it("shows empty-state text when latestLab is null", () => {
    render(<RecentlyCard latestLab={null} vitality={null} />);
    expect(screen.getByText("No recent labs yet")).toBeInTheDocument();
  });

  it("renders a custom panel_name from payload when present", () => {
    const customLab: EHRRecordOut = {
      ...LAB_RECORD,
      payload: { ...LAB_RECORD.payload, panel_name: "Metabolic panel" },
    };
    render(<RecentlyCard latestLab={customLab} vitality={null} />);
    expect(screen.getByText("Metabolic panel")).toBeInTheDocument();
  });

  // ── Score row ────────────────────────────────────────────────────────────────

  it("shows vitality up direction and delta when score increased", () => {
    render(<RecentlyCard latestLab={null} vitality={VITALITY_WITH_TREND} />);
    // delta = 71 - 68 = 3 → "Vitality up 3 · 68 → 71"
    expect(screen.getByText(/Vitality up 3/)).toBeInTheDocument();
    expect(screen.getByText(/68 → 71/)).toBeInTheDocument();
  });

  it("shows vitality down direction when score decreased", () => {
    render(<RecentlyCard latestLab={null} vitality={VITALITY_DOWN} />);
    // delta = 68 - 72 = -4 → "Vitality down 4 · 72 → 68"
    expect(screen.getByText(/Vitality down 4/)).toBeInTheDocument();
    expect(screen.getByText(/72 → 68/)).toBeInTheDocument();
  });

  it("shows a good chip (▲) when score increased", () => {
    render(<RecentlyCard latestLab={null} vitality={VITALITY_WITH_TREND} />);
    expect(screen.getByText(/▲ 3 pts/)).toBeInTheDocument();
  });

  it("shows a warn chip (▼) when score decreased", () => {
    render(<RecentlyCard latestLab={null} vitality={VITALITY_DOWN} />);
    expect(screen.getByText(/▼ 4 pts/)).toBeInTheDocument();
  });

  it("shows steady text when delta is zero", () => {
    render(<RecentlyCard latestLab={null} vitality={VITALITY_FLAT} />);
    expect(screen.getByText(/Vitality steady/)).toBeInTheDocument();
    expect(screen.getByText("Flat")).toBeInTheDocument();
  });

  it("shows 'Score is steady' empty-state when vitality is null", () => {
    render(<RecentlyCard latestLab={null} vitality={null} />);
    expect(screen.getByText("Score is steady")).toBeInTheDocument();
  });

  it("shows current score when trend has fewer than 2 points", () => {
    render(<RecentlyCard latestLab={null} vitality={VITALITY_NO_TREND} />);
    // Falls back to current score row with "Steady" chip
    expect(screen.getByText(/Vitality score 71/)).toBeInTheDocument();
    expect(screen.getByText("Steady")).toBeInTheDocument();
  });

  // ── Full card ────────────────────────────────────────────────────────────────

  it("renders both rows when both lab and vitality are present", () => {
    render(<RecentlyCard latestLab={LAB_RECORD} vitality={VITALITY_WITH_TREND} />);
    expect(screen.getByText("Lipid panel")).toBeInTheDocument();
    expect(screen.getByText(/Vitality up 3/)).toBeInTheDocument();
  });

  it("renders both empty states when no data", () => {
    render(<RecentlyCard latestLab={null} vitality={null} />);
    expect(screen.getByText("No recent labs yet")).toBeInTheDocument();
    expect(screen.getByText("Score is steady")).toBeInTheDocument();
  });
});
