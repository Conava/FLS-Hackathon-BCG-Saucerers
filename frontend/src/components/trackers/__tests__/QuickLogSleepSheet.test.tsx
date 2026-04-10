/**
 * Smoke tests for QuickLogSleepSheet.
 *
 * Mocks the API client so tests stay fast and isolated.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuickLogSleepSheet } from "../QuickLogSleepSheet";

// ---------------------------------------------------------------------------
// Mock API client
// ---------------------------------------------------------------------------

vi.mock("@/lib/api/client", () => ({
  createDailyLog: vi.fn(),
}));

// Import the mocked module so we can control return values per test
import * as apiClient from "@/lib/api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockLog = {
  id: 1,
  patient_id: "PT0199",
  date: "2026-04-09",
  logged_at: "2026-04-09T08:00:00",
  sleep_hours: 7.5,
  sleep_quality: 3,
};

function setup(overrides?: Partial<Parameters<typeof QuickLogSleepSheet>[0]>) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    onSubmitted: vi.fn(),
    ...overrides,
  };
  const result = render(<QuickLogSleepSheet {...props} />);
  return { ...result, props };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("QuickLogSleepSheet", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders the sheet title when open", () => {
    setup();
    expect(screen.getByText("Log sleep")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    setup({ open: false });
    expect(screen.queryByText("Log sleep")).not.toBeInTheDocument();
  });

  it("renders the sleep hours input with default value 7.5", () => {
    setup();
    const input = screen.getByLabelText(/sleep hours/i) as HTMLInputElement;
    expect(input.value).toBe("7.5");
  });

  it("renders 5 quality buttons labeled 1-5", () => {
    setup();
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByRole("button", { name: String(i) })).toBeInTheDocument();
    }
  });

  it("calls createDailyLog with sleep_hours and sleep_quality on Save", async () => {
    vi.mocked(apiClient.createDailyLog).mockResolvedValue(mockLog as never);

    setup();

    // Change sleep hours to 8
    const input = screen.getByLabelText(/sleep hours/i);
    fireEvent.change(input, { target: { value: "8" } });

    // Select quality 4
    fireEvent.click(screen.getByRole("button", { name: "4" }));

    // Click Save
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(apiClient.createDailyLog).toHaveBeenCalledTimes(1);
    });

    const callArg = vi.mocked(apiClient.createDailyLog).mock.calls[0]![0];
    expect(callArg.sleep_hours).toBe(8);
    expect(callArg.sleep_quality).toBe(4);
  });

  it("calls onSubmitted and closes the sheet after successful save", async () => {
    vi.mocked(apiClient.createDailyLog).mockResolvedValue(mockLog as never);

    const { props } = setup();

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(props.onSubmitted).toHaveBeenCalledTimes(1);
      expect(props.onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("shows an inline error and keeps the sheet open on API failure", async () => {
    vi.mocked(apiClient.createDailyLog).mockRejectedValue(
      new Error("API error 500: Internal Server Error"),
    );

    const { props } = setup();

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    // Sheet stays open — onOpenChange not called with false
    expect(props.onOpenChange).not.toHaveBeenCalledWith(false);
    expect(props.onSubmitted).not.toHaveBeenCalled();
  });

  it("calls onOpenChange(false) when Cancel is clicked", () => {
    setup();
    const { props } = setup();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(props.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("highlights the selected quality button with accent styling", () => {
    setup();
    const btn4 = screen.getByRole("button", { name: "4" });
    fireEvent.click(btn4);
    // The selected button should carry the data-selected attribute
    expect(btn4).toHaveAttribute("data-selected", "true");
  });
});
