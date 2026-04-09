/**
 * Tests for the RecordsQA client component.
 *
 * [unit] Tests cover:
 * - Renders the Q&A input with placeholder copy
 * - Renders the AiDisclosureBanner
 * - On submit, shows loading state
 * - Renders the AI answer after mock API resolves
 * - Renders Citation chips for each source in the response
 * - Shows empty answer gracefully
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RecordsQA } from "../RecordsQA";
import * as apiClient from "@/lib/api/client";
import type { RecordsQAResponse } from "@/lib/api/schemas";

// Mock the api client module
vi.mock("@/lib/api/client", () => ({
  postRecordsQA: vi.fn(),
}));

const mockPostRecordsQA = vi.mocked(apiClient.postRecordsQA);

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

  it("shows loading state while request is in flight", async () => {
    // Resolve only after we check loading state
    let resolve!: (v: RecordsQAResponse) => void;
    mockPostRecordsQA.mockReturnValue(
      new Promise<RecordsQAResponse>((res) => {
        resolve = res;
      }),
    );

    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "What are my latest labs?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    // Loading indicator should appear immediately
    expect(screen.getByRole("status")).toBeInTheDocument();

    // Resolve the promise to clean up
    resolve({
      ai_meta: {
        model: "gemini",
        prompt_name: "records_qa",
        request_id: "req-1",
        token_in: 10,
        token_out: 20,
        latency_ms: 100,
      },
      answer: "Your labs look normal.",
      citations: [],
    });
  });

  it("renders the AI answer after successful submission", async () => {
    const mockResponse: RecordsQAResponse = {
      ai_meta: {
        model: "gemini",
        prompt_name: "records_qa",
        request_id: "req-1",
        token_in: 10,
        token_out: 20,
        latency_ms: 100,
      },
      answer: "Your latest HbA1c is within a healthy range.",
      citations: [],
    };

    mockPostRecordsQA.mockResolvedValue(mockResponse);

    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "What is my HbA1c?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Your latest HbA1c is within a healthy range."),
      ).toBeInTheDocument();
    });
  });

  it("renders Citation chips for each source citation", async () => {
    const mockResponse: RecordsQAResponse = {
      ai_meta: {
        model: "gemini",
        prompt_name: "records_qa",
        request_id: "req-2",
        token_in: 15,
        token_out: 30,
        latency_ms: 120,
      },
      answer: "Based on your records, your cholesterol is elevated.",
      citations: [
        { record_id: 42, snippet: "LDL 145 mg/dL" },
        { record_id: 99, snippet: "Total cholesterol 220 mg/dL" },
      ],
    };

    mockPostRecordsQA.mockResolvedValue(mockResponse);

    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "What about my cholesterol?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      // Two citation chips should appear
      expect(screen.getByRole("button", { name: /citation 1/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /citation 2/i })).toBeInTheDocument();
    });
  });

  it("calls postRecordsQA with the typed question", async () => {
    mockPostRecordsQA.mockResolvedValue({
      ai_meta: {
        model: "gemini",
        prompt_name: "records_qa",
        request_id: "req-3",
        token_in: 5,
        token_out: 10,
        latency_ms: 80,
      },
      answer: "Looks good.",
      citations: [],
    });

    render(<RecordsQA />);
    const input = screen.getByPlaceholderText(/ask a question about your records/i);
    fireEvent.change(input, { target: { value: "How is my blood pressure?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(mockPostRecordsQA).toHaveBeenCalledWith("How is my blood pressure?");
    });
  });

  it("does not submit if input is empty", () => {
    render(<RecordsQA />);
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(mockPostRecordsQA).not.toHaveBeenCalled();
  });
});
