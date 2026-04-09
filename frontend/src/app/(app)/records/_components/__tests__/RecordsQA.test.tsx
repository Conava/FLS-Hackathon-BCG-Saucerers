/**
 * Tests for the RecordsQA client component.
 *
 * [unit] Tests cover:
 * - Renders the Q&A input with placeholder copy
 * - Renders the AiDisclosureBanner
 * - Renders a submit button
 * - On submit, calls router.push with the encoded question routed to /coach
 * - Does not navigate if input is empty
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RecordsQA } from "../RecordsQA";

// Mock next/navigation router
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("RecordsQA", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the question input with placeholder text", () => {
    render(<RecordsQA />);
    expect(
      screen.getByPlaceholderText(/ask a question about your records/i),
    ).toBeInTheDocument();
  });

  it("renders the AI disclosure banner", () => {
    render(<RecordsQA />);
    expect(screen.getByRole("note")).toBeInTheDocument();
    expect(screen.getByText(/you're talking to an ai/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<RecordsQA />);
    expect(screen.getByRole("button", { name: /ask/i })).toBeInTheDocument();
  });

  it("navigates to /coach with encoded question on submit", () => {
    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "What are my latest labs?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    expect(mockPush).toHaveBeenCalledWith(
      `/coach?q=${encodeURIComponent("What are my latest labs?")}`,
    );
  });

  it("encodes special characters in the question", () => {
    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "HbA1c & cholesterol?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    expect(mockPush).toHaveBeenCalledWith(
      `/coach?q=${encodeURIComponent("HbA1c & cholesterol?")}`,
    );
  });

  it("does not navigate if input is empty", () => {
    render(<RecordsQA />);
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("does not navigate if input is only whitespace", () => {
    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(mockPush).not.toHaveBeenCalled();
  });
});
