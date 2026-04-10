/**
 * Smoke tests for QuickLogWaterSheet.
 *
 * Uses vi.fn() to mock global fetch so tests remain fast and isolated.
 * Tests: render when open, quick-add buttons set value, submit calls createDailyLog.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuickLogWaterSheet } from "../QuickLogWaterSheet";

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

function mockResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as unknown as Response;
}

const DAILY_LOG_OUT = {
  id: 1,
  patient_id: "PT0199",
  date: "2026-04-09",
  logged_at: "2026-04-09T08:00:00",
  water_ml: 500,
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse(DAILY_LOG_OUT)));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("QuickLogWaterSheet", () => {
  it("renders the title 'Log water' when open", () => {
    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );
    expect(screen.getByText("Log water")).toBeInTheDocument();
  });

  it("does not render content when closed", () => {
    render(
      <QuickLogWaterSheet open={false} onOpenChange={vi.fn()} />
    );
    expect(screen.queryByText("Log water")).not.toBeInTheDocument();
  });

  it("renders all three quick-add buttons (+250 ml, +500 ml, +750 ml)", () => {
    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );
    expect(screen.getByRole("button", { name: /\+250\s*ml/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /\+500\s*ml/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /\+750\s*ml/i })).toBeInTheDocument();
  });

  it("tapping +500 ml sets the input value to 500", () => {
    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: /\+500\s*ml/i }));
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("500");
  });

  it("tapping +250 ml sets the input value to 250", () => {
    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: /\+250\s*ml/i }));
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("250");
  });

  it("tapping +750 ml sets the input value to 750", () => {
    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: /\+750\s*ml/i }));
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.value).toBe("750");
  });

  it("calls createDailyLog with water_ml: 500 on submit after tapping +500", async () => {
    const onOpenChange = vi.fn();
    const onSubmitted = vi.fn();
    render(
      <QuickLogWaterSheet
        open={true}
        onOpenChange={onOpenChange}
        onSubmitted={onSubmitted}
      />
    );

    // Tap +500
    fireEvent.click(screen.getByRole("button", { name: /\+500\s*ml/i }));

    // Submit the form
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(call[0]).toBe("/api/proxy/daily-log");
    expect(call[1].method).toBe("POST");

    const body = JSON.parse(call[1].body as string) as Record<string, unknown>;
    expect(body.water_ml).toBe(500);
  });

  it("calls onSubmitted after a successful save", async () => {
    const onSubmitted = vi.fn();
    render(
      <QuickLogWaterSheet
        open={true}
        onOpenChange={vi.fn()}
        onSubmitted={onSubmitted}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /\+500\s*ml/i }));
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(onSubmitted).toHaveBeenCalledTimes(1);
    });
  });

  it("calls onOpenChange(false) to close after successful save", async () => {
    const onOpenChange = vi.fn();
    render(
      <QuickLogWaterSheet
        open={true}
        onOpenChange={onOpenChange}
        onSubmitted={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /\+500\s*ml/i }));
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("shows an inline error message when the API call fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockResponse({ error: "Server error" }, 500)),
    );

    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );

    fireEvent.click(screen.getByRole("button", { name: /\+250\s*ml/i }));
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("renders a number input with min 50, max 3000, step 50", () => {
    render(
      <QuickLogWaterSheet open={true} onOpenChange={vi.fn()} />
    );
    const input = screen.getByRole("spinbutton") as HTMLInputElement;
    expect(input.min).toBe("50");
    expect(input.max).toBe("3000");
    expect(input.step).toBe("50");
  });
});
