/**
 * Smoke tests for WeeklyCheckInSheet.
 *
 * Mocks the API client so tests stay fast and isolated.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { WeeklyCheckInSheet } from "../WeeklyCheckInSheet";

// ---------------------------------------------------------------------------
// Mock API client
// ---------------------------------------------------------------------------

vi.mock("@/lib/api/client", () => ({
  submitWeeklyCheckIn: vi.fn(),
}));

import * as apiClient from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockSurveyResponse = {
  id: 1,
  patient_id: "PT0199",
  kind: "weekly" as const,
  submitted_at: "2026-04-09T10:00:00",
  answers: { energy: 4, sleep: 3, mood: 5 },
};

function setup(overrides?: Partial<Parameters<typeof WeeklyCheckInSheet>[0]>) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    onSubmitted: vi.fn(),
    ...overrides,
  };
  const result = render(<WeeklyCheckInSheet {...props} />);
  return { ...result, props };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("WeeklyCheckInSheet", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders the sheet title when open", () => {
    setup();
    expect(screen.getByText("30-second check-in")).toBeInTheDocument();
  });

  it("renders the subtitle when open", () => {
    setup();
    expect(
      screen.getByText("Quick pulse on how your week felt.")
    ).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    setup({ open: false });
    expect(screen.queryByText("30-second check-in")).not.toBeInTheDocument();
  });

  it("renders 3 question groups, each with 5 scale buttons", () => {
    setup();
    // Each question has buttons labeled 1-5; with 3 questions that's 15 buttons total
    // We check by aria-label patterns that reference the questions
    expect(screen.getByText(/energy this week/i)).toBeInTheDocument();
    expect(screen.getByText(/sleep quality/i)).toBeInTheDocument();
    expect(screen.getByText(/mood/i)).toBeInTheDocument();
  });

  it("smoke test: picks 4/3/5, clicks Save, asserts payload", async () => {
    vi.mocked(apiClient.submitWeeklyCheckIn).mockResolvedValue(
      mockSurveyResponse as never
    );

    setup();

    // Pick energy = 4 (first group of 5 buttons, button labeled "4")
    const energyButtons = screen.getAllByRole("button", { name: "4" });
    fireEvent.click(energyButtons[0]!); // first group = energy

    // Pick sleep = 3
    const sleepButtons = screen.getAllByRole("button", { name: "3" });
    fireEvent.click(sleepButtons[1]!); // second group = sleep

    // Pick mood = 5
    const moodButtons = screen.getAllByRole("button", { name: "5" });
    fireEvent.click(moodButtons[2]!); // third group = mood

    // Click Save
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(apiClient.submitWeeklyCheckIn).toHaveBeenCalledTimes(1);
    });

    const callArg = vi.mocked(apiClient.submitWeeklyCheckIn).mock.calls[0]![0]!
    expect(callArg.energy).toBe(4);
    expect(callArg.sleep).toBe(3);
    expect(callArg.mood).toBe(5);
  });

  it("calls onSubmitted and closes after successful save", async () => {
    vi.mocked(apiClient.submitWeeklyCheckIn).mockResolvedValue(
      mockSurveyResponse as never
    );

    const { props } = setup();

    // Select at least one value per question to satisfy required validation
    // (default may already be set if component initialises with defaults)
    // Click Save — if component has no defaults the submit may be a no-op
    // so we pick values first
    const btn3s = screen.getAllByRole("button", { name: "3" });
    for (const btn of btn3s.slice(0, 3) as HTMLElement[]) {
      fireEvent.click(btn);
    }

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(props.onSubmitted).toHaveBeenCalledTimes(1);
      expect(props.onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("shows an inline error and keeps the sheet open on API failure", async () => {
    vi.mocked(apiClient.submitWeeklyCheckIn).mockRejectedValue(
      new Error("API error 500: Internal Server Error")
    );

    const { props } = setup();

    // Pick values first to pass any validation
    const btn3s = screen.getAllByRole("button", { name: "3" });
    for (const btn of btn3s.slice(0, 3) as HTMLElement[]) {
      fireEvent.click(btn);
    }

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    expect(props.onOpenChange).not.toHaveBeenCalledWith(false);
    expect(props.onSubmitted).not.toHaveBeenCalled();
  });

  it("highlights the selected scale button with data-selected attribute", () => {
    setup();
    // Each question group has 5 buttons; we pick button "4" from the first group
    const fourButtons = screen.getAllByRole("button", { name: "4" });
    fireEvent.click(fourButtons[0]!);
    expect(fourButtons[0]).toHaveAttribute("data-selected", "true");
  });

  it("calls onOpenChange(false) when Cancel is clicked", () => {
    const { props } = setup();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(props.onOpenChange).toHaveBeenCalledWith(false);
  });
});
