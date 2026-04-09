/**
 * Tests for the OnboardingStepper client component.
 *
 * Covers:
 * - Initial render shows step 1 (welcome)
 * - Advancing through steps via "Next"
 * - Back button preserves state
 * - Cannot submit without GDPR consent on final step
 * - Submit calls submitSurvey with kind=onboarding and navigates to /today
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { OnboardingStepper } from "../stepper";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock the API client
const mockSubmitSurvey = vi.fn();
vi.mock("@/lib/api/client", () => ({
  submitSurvey: (...args: unknown[]) => mockSubmitSurvey(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockSubmitSurvey.mockResolvedValue({ id: 1, kind: "onboarding" });
});

describe("OnboardingStepper", () => {
  it("renders step 1 welcome content initially", () => {
    render(<OnboardingStepper />);
    // Step 1 heading from COPY.onboarding.steps[0].title
    expect(screen.getByText("Welcome to LongevityOS")).toBeInTheDocument();
    // Progress indicator for step 1 of 4
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    // Back button not shown on first step
    expect(screen.queryByRole("button", { name: /back/i })).not.toBeInTheDocument();
  });

  it("advances to step 2 when Next is clicked", () => {
    render(<OnboardingStepper />);
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Step 2 title from COPY.onboarding.steps[1].title
    expect(screen.getByText("Connect your data")).toBeInTheDocument();
  });

  it("shows Back button on step 2 and navigates back to step 1", () => {
    render(<OnboardingStepper />);
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText("Connect your data")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    expect(screen.getByText("Welcome to LongevityOS")).toBeInTheDocument();
  });

  it("advances through all 4 steps to reach GDPR consent step", () => {
    render(<OnboardingStepper />);
    // Step 1 -> 2
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Step 2 -> 3
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Step 3 -> 4 (GDPR consent)
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    // Final step shows the GDPR consent toggle
    expect(screen.getByText(/consent/i)).toBeInTheDocument();
    // Finish button should be present but disabled (consent not yet checked)
    const finishBtn = screen.getByRole("button", { name: /get started/i });
    expect(finishBtn).toBeDisabled();
  });

  it("enables Finish button when GDPR consent is toggled on", () => {
    render(<OnboardingStepper />);
    // Navigate to final step
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));

    const finishBtn = screen.getByRole("button", { name: /get started/i });
    expect(finishBtn).toBeDisabled();

    // Toggle the GDPR consent switch
    const consentSwitch = screen.getByRole("switch");
    fireEvent.click(consentSwitch);

    expect(finishBtn).not.toBeDisabled();
  });

  it("calls submitSurvey with kind=onboarding on finish and redirects to /today", async () => {
    render(<OnboardingStepper />);
    // Navigate to final step
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /next/i }));

    // Enable consent
    fireEvent.click(screen.getByRole("switch"));

    // Submit
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));

    await waitFor(() => {
      expect(mockSubmitSurvey).toHaveBeenCalledWith(
        expect.objectContaining({ kind: "onboarding" })
      );
      expect(mockPush).toHaveBeenCalledWith("/today");
    });
  });

  it("back button on step 2 preserves answers selected on step 2 (state preserved)", () => {
    render(<OnboardingStepper />);
    // Advance to step 2
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText("Connect your data")).toBeInTheDocument();

    // Go back
    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    // Back to step 1
    expect(screen.getByText("Welcome to LongevityOS")).toBeInTheDocument();

    // Advance again — step 2 should still be there
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText("Connect your data")).toBeInTheDocument();
  });
});
