/**
 * Tests for Insights screen and FutureSelfSimulator component.
 *
 * The InsightsPage is a server component — we test the signal card grid and
 * risk flag list by testing the pure-render output of sub-components.
 *
 * FutureSelfSimulator is a client component — we test it with mocked
 * postFutureSelf calls.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// Mock the API client module
vi.mock("@/lib/api/client", () => ({
  postFutureSelf: vi.fn(),
}));

import { FutureSelfSimulator } from "../_components/FutureSelfSimulator";
import * as apiClient from "@/lib/api/client";

// ─── FutureSelfSimulator ──────────────────────────────────────────────────────

describe("FutureSelfSimulator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the three slider labels", () => {
    render(<FutureSelfSimulator />);
    expect(screen.getByText(/sleep/i)).toBeInTheDocument();
    expect(screen.getByText(/activity/i)).toBeInTheDocument();
    expect(screen.getByText(/alcohol/i)).toBeInTheDocument();
  });

  it("renders the AI disclosure banner", () => {
    render(<FutureSelfSimulator />);
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("renders all three sliders", () => {
    render(<FutureSelfSimulator />);
    const sliders = screen.getAllByRole("slider");
    expect(sliders).toHaveLength(3);
  });

  it("shows loading state while fetching future-self projection", async () => {
    // Delay the resolution so we can observe loading state
    let resolve: (v: { bio_age: number; narrative: string; ai_meta: object; disclaimer?: string }) => void;
    const promise = new Promise<{ bio_age: number; narrative: string; ai_meta: object; disclaimer?: string }>(
      (res) => { resolve = res; }
    );
    vi.mocked(apiClient.postFutureSelf).mockReturnValue(promise as ReturnType<typeof apiClient.postFutureSelf>);

    render(<FutureSelfSimulator />);

    // Trigger a slider change (fire on sleep slider)
    const sliders = screen.getAllByRole("slider");
    const sleepSlider = sliders[0];
    if (!sleepSlider) throw new Error("Sleep slider not found");
    act(() => {
      fireEvent.keyDown(sleepSlider, { key: "ArrowRight" });
    });

    // debounce is 400ms — wait a bit then check loading
    await act(async () => {
      await new Promise((r) => setTimeout(r, 450));
    });

    expect(screen.getByText(/projecting/i)).toBeInTheDocument();

    // Resolve the promise
    act(() => {
      resolve!({
        bio_age: 65,
        narrative: "Great outlook.",
        ai_meta: { model: "gemini", prompt_name: "p", request_id: "r", token_in: 1, token_out: 1, latency_ms: 1 },
      });
    });

    await waitFor(() => {
      expect(screen.queryByText(/projecting/i)).not.toBeInTheDocument();
    });
  });

  it("displays projected biological age after response resolves", async () => {
    vi.mocked(apiClient.postFutureSelf).mockResolvedValue({
      bio_age: 63,
      narrative: "Looking good.",
      ai_meta: { model: "gemini", prompt_name: "p", request_id: "r", token_in: 1, token_out: 1, latency_ms: 1 },
    });

    render(<FutureSelfSimulator />);

    const sliders = screen.getAllByRole("slider");
    const sleepSlider = sliders[0];
    if (!sleepSlider) throw new Error("Sleep slider not found");
    act(() => {
      fireEvent.keyDown(sleepSlider, { key: "ArrowRight" });
    });

    // Wait for debounce and response
    await act(async () => {
      await new Promise((r) => setTimeout(r, 450));
    });

    await waitFor(() => {
      expect(screen.getByText(/63/)).toBeInTheDocument();
    });
  });
});
