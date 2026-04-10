import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuickLogWorkoutSheet } from "../QuickLogWorkoutSheet";
import * as apiClient from "@/lib/api/client";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  createDailyLog: vi.fn(),
}));

describe("QuickLogWorkoutSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the title when open", () => {
    render(
      <QuickLogWorkoutSheet
        open={true}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.getByRole("heading", { name: "Log workout" })).toBeInTheDocument();
  });

  it("does not render content when closed", () => {
    render(
      <QuickLogWorkoutSheet
        open={false}
        onOpenChange={vi.fn()}
      />
    );
    expect(screen.queryByText("Log workout")).not.toBeInTheDocument();
  });

  it("renders all 6 workout type tiles", () => {
    render(
      <QuickLogWorkoutSheet open={true} onOpenChange={vi.fn()} />
    );
    expect(screen.getByText(/walk/i)).toBeInTheDocument();
    expect(screen.getByText(/run/i)).toBeInTheDocument();
    expect(screen.getByText(/bike/i)).toBeInTheDocument();
    expect(screen.getByText(/strength/i)).toBeInTheDocument();
    expect(screen.getByText(/yoga/i)).toBeInTheDocument();
    expect(screen.getByText(/other/i)).toBeInTheDocument();
  });

  it("renders intensity pill buttons", () => {
    render(
      <QuickLogWorkoutSheet open={true} onOpenChange={vi.fn()} />
    );
    expect(screen.getByRole("button", { name: /low/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /high/i })).toBeInTheDocument();
  });

  it("renders duration input with default value 30", () => {
    render(
      <QuickLogWorkoutSheet open={true} onOpenChange={vi.fn()} />
    );
    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue(30);
  });

  it("smoke test: pick run, 45 min, high → createDailyLog payload matches", async () => {
    const today = new Date().toISOString().split("T")[0];
    const onSubmitted = vi.fn();
    const onOpenChange = vi.fn();

    vi.mocked(apiClient.createDailyLog).mockResolvedValueOnce({} as never);

    render(
      <QuickLogWorkoutSheet
        open={true}
        onOpenChange={onOpenChange}
        onSubmitted={onSubmitted}
      />
    );

    // Pick "run" workout type
    fireEvent.click(screen.getByText(/run/i));

    // Set duration to 45
    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "45" } });

    // Pick "High" intensity
    fireEvent.click(screen.getByRole("button", { name: /high/i }));

    // Submit
    fireEvent.click(screen.getByRole("button", { name: /log workout/i }));

    await waitFor(() => {
      expect(apiClient.createDailyLog).toHaveBeenCalledWith({
        date: today,
        workout_minutes: 45,
        workout_type: "run",
        workout_intensity: "high",
      });
    });

    await waitFor(() => {
      expect(onSubmitted).toHaveBeenCalledTimes(1);
    });
  });
});
