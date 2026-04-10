/**
 * Tests for the FutureSelfSimulator client component.
 *
 * Updated to match the mockup-rebuilt FutureSelfSimulator:
 *   - AI disclosure banner moved to parent page (server component)
 *   - Section shows "Future-self simulator" heading + "10Y Horizon" chip
 *   - Two-column projected age display: "Current path" (71) | "Improved path" (64)
 *   - "Apply to my outlook" CTA button
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";

// Mock the API client module
vi.mock("@/lib/api/client", () => ({
  postFutureSelf: vi.fn(),
}));

import { FutureSelfSimulator } from "../_components/FutureSelfSimulator";
import * as apiClient from "@/lib/api/client";

// -- FutureSelfSimulator ------------------------------------------------------

describe("FutureSelfSimulator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the three slider labels", () => {
    render(<FutureSelfSimulator />);
    expect(screen.getByText(/^sleep$/i)).toBeInTheDocument();
    expect(screen.getByText(/^activity$/i)).toBeInTheDocument();
    expect(screen.getByText(/^alcohol$/i)).toBeInTheDocument();
  });

  it("renders the section header and chip", () => {
    render(<FutureSelfSimulator />);
    // AI disclosure banner is now in the parent page (server component).
    // The simulator renders a heading and 10Y Horizon chip.
    expect(screen.getByText(/future-self simulator/i)).toBeInTheDocument();
    expect(screen.getByText(/10Y Horizon/i)).toBeInTheDocument();
  });

  it("renders all three sliders", () => {
    render(<FutureSelfSimulator />);
    const sliders = screen.getAllByRole("slider");
    expect(sliders).toHaveLength(3);
  });

  it("renders the projected age section with current and improved path", () => {
    render(<FutureSelfSimulator />);
    expect(screen.getByText(/current path/i)).toBeInTheDocument();
    expect(screen.getByText(/improved path/i)).toBeInTheDocument();
    // Default demo values
    expect(screen.getByText("71")).toBeInTheDocument();
    expect(screen.getByText("64")).toBeInTheDocument();
  });

  it("renders the Apply CTA button", () => {
    render(<FutureSelfSimulator />);
    expect(
      screen.getByRole("button", { name: /apply to my outlook/i }),
    ).toBeInTheDocument();
  });

  it("displays projected biological age after response resolves", async () => {
    vi.mocked(apiClient.postFutureSelf).mockResolvedValue({
      bio_age: 63,
      narrative: "Looking good.",
      ai_meta: {
        model: "gemini",
        prompt_name: "p",
        request_id: "r",
        token_in: 1,
        token_out: 1,
        latency_ms: 1,
      },
    });

    render(<FutureSelfSimulator />);

    // Directly call scheduleProjection by triggering the slider's onValueChange
    // via the Radix slider's internal DOM (keyboard interaction in JSDOM is limited).
    // We test the API integration by calling the mock directly through the hook.
    const sliders = screen.getAllByRole("slider");
    const sleepSlider = sliders[0];
    if (!sleepSlider) throw new Error("Sleep slider not found");

    // Simulate slider pointer down + keyboard change
    act(() => {
      sleepSlider.focus();
      // Dispatch a custom event that Radix slider picks up
      sleepSlider.dispatchEvent(
        new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
      );
    });

    // Wait for debounce + API response
    await act(async () => {
      await new Promise((r) => setTimeout(r, 450));
    });

    // After API resolves, improved path should show 63
    await waitFor(() => {
      expect(screen.getByText("63")).toBeInTheDocument();
    });
  });
});
