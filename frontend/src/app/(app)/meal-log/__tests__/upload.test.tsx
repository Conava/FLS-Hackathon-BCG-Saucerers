/**
 * Unit tests for the MealLogUpload client component.
 *
 * Mocks:
 *  - `next/navigation` (useRouter) — avoids Next.js router context requirement
 *  - `@/lib/api/client` uploadMealLog — avoids real fetch calls
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MealLogUpload } from "../upload";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}));

// jsdom doesn't implement URL.createObjectURL — provide a stub
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
global.URL.revokeObjectURL = vi.fn();

const mockUpload = vi.fn();

vi.mock("@/lib/api/client", () => ({
  uploadMealLog: (...args: unknown[]) => mockUpload(...args),
  getMealLogs: vi.fn().mockResolvedValue({ patient_id: "PT0199", logs: [] }),
}));

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const FAKE_ANALYSIS = {
  classification: "Mediterranean Bowl",
  macros: {
    kcal: 520,
    protein_g: 32,
    carbs_g: 45,
    fat_g: 18,
    fiber_g: 8,
    polyphenols_mg: 120,
  },
  longevity_swap: "Replace white rice with quinoa",
  swap_rationale: "Quinoa has a lower glycaemic index and more fibre",
};

const FAKE_RESPONSE = {
  ai_meta: {
    model: "gemini-2.5-flash",
    prompt_name: "meal_vision",
    request_id: "req-1",
    token_in: 400,
    token_out: 150,
    latency_ms: 1800,
  },
  meal_log_id: 42,
  photo_uri: "gs://bucket/meal/42.jpg",
  analysis: FAKE_ANALYSIS,
  disclaimer: "Wellness guidance only.",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MealLogUpload", () => {
  beforeEach(() => {
    mockUpload.mockReset();
  });

  it("renders the page title 'Meal vision'", () => {
    render(<MealLogUpload />);
    expect(screen.getByText("Meal vision")).toBeInTheDocument();
  });

  it("renders a file input that accepts images", () => {
    const { container } = render(<MealLogUpload />);
    const input = container.querySelector("input[type='file']");
    expect(input).toBeInTheDocument();
    expect(input?.getAttribute("accept")).toContain("image/*");
  });

  it("shows the AI disclosure banner", () => {
    render(<MealLogUpload />);
    // AI banner has role="note"
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("shows the AI meal analysis text in the banner", () => {
    render(<MealLogUpload />);
    expect(
      screen.getByText(/AI meal analysis/i)
    ).toBeInTheDocument();
  });

  it("analyze button is disabled before a file is selected", () => {
    render(<MealLogUpload />);
    // Analyze button only appears after file is selected — before that there
    // is only a "Take a photo" button. Verify no enabled analyze button.
    const analyzeBtn = screen.queryByRole("button", { name: /analyze my meal/i });
    expect(analyzeBtn).toBeNull();
  });

  it("shows loading state after file select + analyze click", async () => {
    // Upload hangs so we can observe the loading state
    mockUpload.mockReturnValue(new Promise(() => {}));

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    const btn = screen.getByRole("button", { name: /analyze my meal/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getByText(/looking at your plate/i)).toBeInTheDocument();
    });
  });

  it("renders meal analysis result on successful upload", async () => {
    mockUpload.mockResolvedValue(FAKE_RESPONSE);

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => {
      expect(screen.getByText("Mediterranean Bowl")).toBeInTheDocument();
    });

    // Longevity swap shown
    expect(screen.getByText(/replace white rice with quinoa/i)).toBeInTheDocument();
  });

  it("shows the 'Log to today' button after a successful analysis", async () => {
    mockUpload.mockResolvedValue(FAKE_RESPONSE);

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /log to today/i })
      ).toBeInTheDocument();
    });
  });

  it("shows 'Analyze but don't store photo' ghost button after analysis", async () => {
    mockUpload.mockResolvedValue(FAKE_RESPONSE);

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/analyze but don/i)
      ).toBeInTheDocument();
    });
  });

  it("shows the footer disclaimer", () => {
    render(<MealLogUpload />);
    expect(
      screen.getByText(/Meal vision is a wellness tool/i)
    ).toBeInTheDocument();
  });

  it("shows an error message when upload fails", async () => {
    mockUpload.mockRejectedValue(new Error("API error 500: server error"));

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/analyse this image/i)
      ).toBeInTheDocument();
    });
  });

  it("passes a FormData with 'file' key to uploadMealLog", async () => {
    mockUpload.mockResolvedValue(FAKE_RESPONSE);

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => expect(mockUpload).toHaveBeenCalledOnce());

    const formData = (mockUpload.mock.calls[0] as [FormData])[0];
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBe(file);
  });

  it("shows the DETECTED label and macro chips after analysis", async () => {
    mockUpload.mockResolvedValue(FAKE_RESPONSE);

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => {
      expect(screen.getByText("Detected")).toBeInTheDocument();
    });

    // Macro chips
    expect(screen.getByText(/520 kcal/)).toBeInTheDocument();
    expect(screen.getByText(/32g protein/)).toBeInTheDocument();
  });

  it("shows the ✓ Analyzed tag after successful analysis", async () => {
    mockUpload.mockResolvedValue(FAKE_RESPONSE);

    render(<MealLogUpload />);

    const file = new File(["(jpeg-data)"], "meal.jpg", { type: "image/jpeg" });
    const input = screen.getByTestId("meal-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /analyze my meal/i }));

    await waitFor(() => {
      expect(screen.getByText(/✓ Analyzed/)).toBeInTheDocument();
    });
  });
});
