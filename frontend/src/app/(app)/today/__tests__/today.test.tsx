/**
 * Tests for Today screen components.
 *
 * The server component (page.tsx) does direct backend fetches — we test
 * the client subcomponents in isolation with mocked data.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProtocolList } from "../_components/ProtocolList";
import { VitalityTap } from "../_components/VitalityTap";
import { SignalsSheet } from "../_components/SignalsSheet";
import { QuickLogGrid } from "../_components/QuickLogGrid";
import type { ProtocolActionOut } from "@/lib/api/schemas";
import type { InsightOut } from "@/lib/api/schemas";

// ── Mock the API client (only client-side calls go through proxy) ─────────────
vi.mock("@/lib/api/client", () => ({
  completeProtocolAction: vi.fn().mockResolvedValue({
    action_id: 1,
    streak_days: 5,
    completed_at: "2026-04-09T10:00:00Z",
  }),
  skipProtocolAction: vi.fn().mockResolvedValue({ id: 1 }),
  reorderProtocolActions: vi.fn().mockResolvedValue(undefined),
  createManualMealLog: vi.fn().mockResolvedValue({}),
  createDailyLog: vi.fn().mockResolvedValue({}),
  submitWeeklyCheckIn: vi.fn().mockResolvedValue({}),
}));

// ── Mock next/navigation ───────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

// ── Mock tracker sheets so QuickLogGrid tests stay isolated ───────────────────
vi.mock("@/components/trackers/QuickLogMealSheet", () => ({
  QuickLogMealSheet: ({ open }: { open: boolean }) =>
    open ? <div data-testid="meal-sheet">MealSheet</div> : null,
}));
vi.mock("@/components/trackers/QuickLogSleepSheet", () => ({
  QuickLogSleepSheet: ({ open }: { open: boolean }) =>
    open ? <div data-testid="sleep-sheet">SleepSheet</div> : null,
}));
vi.mock("@/components/trackers/QuickLogWorkoutSheet", () => ({
  QuickLogWorkoutSheet: ({ open }: { open: boolean }) =>
    open ? <div data-testid="workout-sheet">WorkoutSheet</div> : null,
}));
vi.mock("@/components/trackers/QuickLogWaterSheet", () => ({
  QuickLogWaterSheet: ({ open }: { open: boolean }) =>
    open ? <div data-testid="water-sheet">WaterSheet</div> : null,
}));

// ── ProtocolList ──────────────────────────────────────────────────────────────

const MOCK_ACTIONS: ProtocolActionOut[] = [
  {
    id: 1,
    protocol_id: 10,
    category: "Nutrition",
    title: "Eat 30g protein at breakfast",
    completed_today: false,
    streak_days: 3,
    dimension: "metabolic",
    rationale: "Supports muscle maintenance",
    target: null,
  },
  {
    id: 2,
    protocol_id: 10,
    category: "Movement",
    title: "Walk 30 minutes",
    completed_today: true,
    streak_days: 7,
    dimension: "cardiovascular",
    rationale: null,
    target: null,
  },
];

describe("ProtocolList", () => {
  it("renders all protocol actions", () => {
    render(<ProtocolList actions={MOCK_ACTIONS} />);
    expect(screen.getByText("Eat 30g protein at breakfast")).toBeInTheDocument();
    expect(screen.getByText("Walk 30 minutes")).toBeInTheDocument();
  });

  it("shows completed state for done actions", () => {
    render(<ProtocolList actions={MOCK_ACTIONS} />);
    // The second action (id=2) is completed_today=true
    const buttons = screen.getAllByRole("button");
    // Second button should have aria-pressed=true
    const completedButton = buttons.find(
      (b) => b.getAttribute("aria-pressed") === "true"
    );
    expect(completedButton).toBeDefined();
  });

  it("shows category tags", () => {
    render(<ProtocolList actions={MOCK_ACTIONS} />);
    expect(screen.getByText("Nutrition")).toBeInTheDocument();
    expect(screen.getByText("Movement")).toBeInTheDocument();
  });

  it("shows rationale for actions that have it", () => {
    render(<ProtocolList actions={MOCK_ACTIONS} />);
    expect(screen.getByText("Supports muscle maintenance")).toBeInTheDocument();
  });

  it("renders empty state when no actions", () => {
    render(<ProtocolList actions={[]} />);
    expect(screen.getByText(/no protocol/i)).toBeInTheDocument();
  });

  it("toggles action optimistically on click", async () => {
    const { completeProtocolAction } = await import("@/lib/api/client");
    render(<ProtocolList actions={MOCK_ACTIONS} />);
    // Click the first (uncompleted) action's toggle button
    const completeButton = screen.getByRole("button", {
      name: /mark as complete/i,
    });
    fireEvent.click(completeButton);
    // Should optimistically update — now 2 "mark as incomplete" buttons (action 1 + action 2)
    await waitFor(() => {
      const incompleteButtons = screen.getAllByRole("button", {
        name: /mark as incomplete/i,
      });
      expect(incompleteButtons).toHaveLength(2);
    });
    expect(completeProtocolAction).toHaveBeenCalledWith(1);
  });
});

// ── VitalityTap ───────────────────────────────────────────────────────────────

const MOCK_INSIGHTS: InsightOut[] = [
  {
    kind: "sleep",
    severity: "low",
    message: "Sleep looks good — 7.5h average",
    signals: ["hrv_rmssd_ms", "sleep_duration_hrs"],
  },
  {
    kind: "cardiovascular",
    severity: "moderate",
    message: "Resting HR slightly elevated",
    signals: ["resting_hr_bpm"],
  },
];

describe("VitalityTap", () => {
  it("renders the VitalityRing", () => {
    render(
      <VitalityTap score={72} delta={3} insights={MOCK_INSIGHTS} />
    );
    // VitalityRing renders score as text
    expect(screen.getByText("72")).toBeInTheDocument();
  });

  it("opens SignalsSheet when ring is tapped", async () => {
    render(
      <VitalityTap score={72} delta={3} insights={MOCK_INSIGHTS} />
    );
    const ringButton = screen.getByRole("button", { name: /view signals/i });
    fireEvent.click(ringButton);
    await waitFor(() => {
      expect(screen.getByText(/longevity signals/i)).toBeInTheDocument();
    });
  });

  it("shows insights in the signals sheet", async () => {
    render(
      <VitalityTap score={72} delta={3} insights={MOCK_INSIGHTS} />
    );
    fireEvent.click(screen.getByRole("button", { name: /view signals/i }));
    await waitFor(() => {
      expect(screen.getByText(/sleep looks good/i)).toBeInTheDocument();
    });
  });
});

// ── SignalsSheet ───────────────────────────────────────────────────────────────

describe("SignalsSheet", () => {
  it("renders sheet title when open", () => {
    render(
      <SignalsSheet
        open={true}
        onClose={vi.fn()}
        insights={MOCK_INSIGHTS}
      />
    );
    expect(screen.getByText(/longevity signals/i)).toBeInTheDocument();
  });

  it("renders a SignalCard per insight", () => {
    render(
      <SignalsSheet
        open={true}
        onClose={vi.fn()}
        insights={MOCK_INSIGHTS}
      />
    );
    expect(screen.getByText(/sleep looks good/i)).toBeInTheDocument();
    expect(screen.getByText(/resting hr slightly elevated/i)).toBeInTheDocument();
  });

  it("does not render content when closed", () => {
    render(
      <SignalsSheet
        open={false}
        onClose={vi.fn()}
        insights={MOCK_INSIGHTS}
      />
    );
    expect(screen.queryByText(/longevity signals/i)).not.toBeInTheDocument();
  });

  it("calls onClose when sheet is dismissed", () => {
    const onClose = vi.fn();
    render(
      <SignalsSheet open={true} onClose={onClose} insights={MOCK_INSIGHTS} />
    );
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows empty state when no insights", () => {
    render(
      <SignalsSheet open={true} onClose={vi.fn()} insights={[]} />
    );
    expect(screen.getByText(/no signals/i)).toBeInTheDocument();
  });
});

// ── QuickLogGrid ──────────────────────────────────────────────────────────────

describe("QuickLogGrid", () => {
  it("renders all 4 quick log buttons", () => {
    render(<QuickLogGrid />);
    expect(screen.getByText("Meal")).toBeInTheDocument();
    expect(screen.getByText("Sleep")).toBeInTheDocument();
    expect(screen.getByText("Workout")).toBeInTheDocument();
    expect(screen.getByText("Water")).toBeInTheDocument();
  });

  it("renders 4 emoji icons", () => {
    render(<QuickLogGrid />);
    expect(screen.getByText("🍽️")).toBeInTheDocument();
    expect(screen.getByText("😴")).toBeInTheDocument();
    expect(screen.getByText("🏃")).toBeInTheDocument();
    expect(screen.getByText("💧")).toBeInTheDocument();
  });

  it("Meal tile is a button (not a link)", () => {
    render(<QuickLogGrid />);
    const mealBtn = screen.getByRole("button", { name: /^meal$/i });
    expect(mealBtn).toBeInTheDocument();
    expect(mealBtn.tagName).toBe("BUTTON");
  });

  it("tapping Meal opens the meal sheet", () => {
    render(<QuickLogGrid />);
    expect(screen.queryByTestId("meal-sheet")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^meal$/i }));
    expect(screen.getByTestId("meal-sheet")).toBeInTheDocument();
  });

  it("tapping Sleep opens the sleep sheet", () => {
    render(<QuickLogGrid />);
    fireEvent.click(screen.getByRole("button", { name: /^sleep$/i }));
    expect(screen.getByTestId("sleep-sheet")).toBeInTheDocument();
  });

  it("tapping Workout opens the workout sheet", () => {
    render(<QuickLogGrid />);
    fireEvent.click(screen.getByRole("button", { name: /^workout$/i }));
    expect(screen.getByTestId("workout-sheet")).toBeInTheDocument();
  });

  it("tapping Water opens the water sheet", () => {
    render(<QuickLogGrid />);
    fireEvent.click(screen.getByRole("button", { name: /^water$/i }));
    expect(screen.getByTestId("water-sheet")).toBeInTheDocument();
  });
});
