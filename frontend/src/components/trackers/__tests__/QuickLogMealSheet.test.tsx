/**
 * Smoke tests for QuickLogMealSheet.
 *
 * Mocks:
 *  - `next/navigation` (useRouter) — avoids Next.js router context
 *  - `@/lib/api/client` createManualMealLog — avoids real fetch calls
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QuickLogMealSheet } from "../QuickLogMealSheet";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockCreateManualMealLog = vi.fn();
vi.mock("@/lib/api/client", () => ({
  createManualMealLog: (...args: unknown[]) => mockCreateManualMealLog(...args),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderSheet(props?: {
  open?: boolean;
  onOpenChange?: (v: boolean) => void;
  onSubmitted?: () => void;
}) {
  return render(
    <QuickLogMealSheet
      open={props?.open ?? true}
      onOpenChange={props?.onOpenChange ?? vi.fn()}
      onSubmitted={props?.onSubmitted}
    />,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("QuickLogMealSheet", () => {
  beforeEach(() => {
    mockCreateManualMealLog.mockReset();
    mockPush.mockReset();
  });

  it("renders the sheet title when open", () => {
    renderSheet();
    expect(screen.getByText(/log a meal/i)).toBeInTheDocument();
  });

  it("renders Name and kcal fields", () => {
    renderSheet();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/kcal/i)).toBeInTheDocument();
  });

  it("renders macro fields: Protein, Carbs, Fat, Fiber", () => {
    renderSheet();
    expect(screen.getByLabelText(/protein/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/carbs/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fat/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fiber/i)).toBeInTheDocument();
  });

  it("renders Notes textarea", () => {
    renderSheet();
    expect(screen.getByLabelText(/notes/i)).toBeInTheDocument();
  });

  it("renders a 'Prefer the camera?' link", () => {
    renderSheet();
    expect(screen.getByText(/prefer the camera/i)).toBeInTheDocument();
  });

  it("clicking 'Prefer the camera?' pushes to /meal-log", () => {
    const onOpenChange = vi.fn();
    renderSheet({ onOpenChange });
    fireEvent.click(screen.getByText(/prefer the camera/i));
    expect(mockPush).toHaveBeenCalledWith("/meal-log");
  });

  it("Save button is present", () => {
    renderSheet();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
  });

  it("fills name + kcal and clicking Save calls createManualMealLog", async () => {
    mockCreateManualMealLog.mockResolvedValue({
      ai_meta: {
        model: "manual",
        prompt_name: "manual",
        request_id: "r1",
        token_in: 0,
        token_out: 0,
        latency_ms: 0,
      },
      meal_log_id: 1,
      photo_uri: "manual://uuid-1",
      analysis: {
        classification: "Pasta",
        macros: {},
        longevity_swap: "",
        swap_rationale: "",
      },
    });

    renderSheet();

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Pasta" },
    });
    fireEvent.change(screen.getByLabelText(/kcal/i), {
      target: { value: "500" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(mockCreateManualMealLog).toHaveBeenCalledOnce();
    });

    const call = mockCreateManualMealLog.mock.calls[0];
    if (!call) throw new Error("createManualMealLog was not called");
    const arg = call[0] as Record<string, unknown>;
    expect(arg.name).toBe("Pasta");
    expect(arg.kcal).toBe(500);
    expect(arg.protein_g).toBe(0);
    expect(arg.carbs_g).toBe(0);
    expect(arg.fat_g).toBe(0);
    expect(arg.fiber_g).toBe(0);
  });

  it("calls onSubmitted after successful save", async () => {
    mockCreateManualMealLog.mockResolvedValue({
      ai_meta: {
        model: "manual",
        prompt_name: "manual",
        request_id: "r1",
        token_in: 0,
        token_out: 0,
        latency_ms: 0,
      },
      meal_log_id: 2,
      photo_uri: "manual://uuid-2",
      analysis: {
        classification: "Salad",
        macros: {},
        longevity_swap: "",
        swap_rationale: "",
      },
    });

    const onSubmitted = vi.fn();
    renderSheet({ onSubmitted });

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Salad" },
    });
    fireEvent.change(screen.getByLabelText(/kcal/i), {
      target: { value: "200" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(onSubmitted).toHaveBeenCalledOnce();
    });
  });

  it("shows error message when createManualMealLog fails", async () => {
    mockCreateManualMealLog.mockRejectedValue(new Error("API error 500"));

    renderSheet();

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "Soup" },
    });
    fireEvent.change(screen.getByLabelText(/kcal/i), {
      target: { value: "150" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText(/API error 500/i)).toBeInTheDocument();
    });
  });

  it("does not render when open is false", () => {
    renderSheet({ open: false });
    expect(screen.queryByText(/log a meal/i)).not.toBeInTheDocument();
  });
});
