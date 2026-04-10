/**
 * Tests for the OnboardingStepper client component.
 *
 * Covers:
 * - Initial render shows step 1 (welcome) with logo tagline and hero title
 * - Advancing through steps via "Continue"
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
    // Tagline
    expect(screen.getByText("Welcome to Helf")).toBeInTheDocument();
    // Hero title
    expect(screen.getByText("Your longevity, in one place.")).toBeInTheDocument();
    // Progress indicator
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    // Back button not shown on first step
    expect(screen.queryByRole("button", { name: /back/i })).not.toBeInTheDocument();
  });

  it("advances to step 2 when Continue is clicked", () => {
    render(<OnboardingStepper />);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    // Step 2 title from COPY.onboarding.steps[1].title
    expect(screen.getByText("Connect your data")).toBeInTheDocument();
  });

  it("shows Back button on step 2 and navigates back to step 1", () => {
    render(<OnboardingStepper />);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByText("Connect your data")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    // Step 1 hero title restored
    expect(screen.getByText("Your longevity, in one place.")).toBeInTheDocument();
  });

  it("advances through all 4 steps to reach GDPR consent step", () => {
    render(<OnboardingStepper />);
    // Step 1 -> 2
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    // Step 2 -> 3
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    // Step 3 -> 4 (GDPR consent)
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    // Final step shows GDPR consent checkbox
    expect(screen.getByText(/consent/i)).toBeInTheDocument();
    // Finish button present but disabled
    const finishBtn = screen.getByRole("button", { name: /finish/i });
    expect(finishBtn).toBeDisabled();
  });

  it("enables Finish button when GDPR consent checkbox is checked", () => {
    render(<OnboardingStepper />);
    // Navigate to final step
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    const finishBtn = screen.getByRole("button", { name: /finish/i });
    expect(finishBtn).toBeDisabled();

    // Check the GDPR consent checkbox
    const consentCheckbox = screen.getByRole("checkbox");
    fireEvent.click(consentCheckbox);

    expect(finishBtn).not.toBeDisabled();
  });

  it("calls submitSurvey with kind=onboarding on finish and redirects to /today", async () => {
    render(<OnboardingStepper />);
    // Navigate to final step
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    // Enable consent
    fireEvent.click(screen.getByRole("checkbox"));

    // Submit
    fireEvent.click(screen.getByRole("button", { name: /finish/i }));

    await waitFor(() => {
      expect(mockSubmitSurvey).toHaveBeenCalledWith(
        expect.objectContaining({ kind: "onboarding" })
      );
      expect(mockPush).toHaveBeenCalledWith("/today");
    });
  });

  it("back button on step 2 preserves state and re-advances to step 2", () => {
    render(<OnboardingStepper />);
    // Advance to step 2
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByText("Connect your data")).toBeInTheDocument();

    // Go back
    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    expect(screen.getByText("Your longevity, in one place.")).toBeInTheDocument();

    // Advance again - step 2 should still be there
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByText("Connect your data")).toBeInTheDocument();
  });

  it("shows progress bar step caption with ~3 min estimate", () => {
    render(<OnboardingStepper />);
    expect(screen.getByText(/step 1 of 4/i)).toBeInTheDocument();
    expect(screen.getByText(/~3 min/i)).toBeInTheDocument();
  });

  it("shows disclaimer text at the bottom", () => {
    render(<OnboardingStepper />);
    expect(
      screen.getByText(/not medical advice\. wellness and lifestyle guidance only\./i)
    ).toBeInTheDocument();
  });
});
