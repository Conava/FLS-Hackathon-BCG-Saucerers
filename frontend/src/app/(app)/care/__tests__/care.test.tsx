/**
 * Care screen tests — render + mocked message post.
 *
 * Server-fetched data is simulated by mocking global fetch.
 * next/headers is mocked to provide a patient_id cookie.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ── Mock next/headers (used by session helper in server component) ──────────
vi.mock("next/headers", () => ({
  cookies: vi.fn().mockResolvedValue({
    get: (name: string) => (name ? { value: "PT0199" } : undefined),
  }),
}));

// ── MessageComposer ──────────────────────────────────────────────────────────
import { MessageComposer } from "../_components/MessageComposer";

describe("MessageComposer", () => {
  it("renders the textarea and send button", () => {
    render(<MessageComposer />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    render(<MessageComposer />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("send button is enabled when input has text", async () => {
    render(<MessageComposer />);
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Hello, doctor" } });
    expect(screen.getByRole("button", { name: /send/i })).not.toBeDisabled();
  });

  it("calls POST /api/proxy/messages on submit", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        patient_id: "PT0199",
        content: "Hello, doctor",
        sent_at: "2026-04-09T10:00:00Z",
        direction: "outbound",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MessageComposer />);
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Hello, doctor" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/proxy/messages",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    vi.unstubAllGlobals();
  });

  it("clears the input after successful send", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        patient_id: "PT0199",
        content: "Hello",
        sent_at: "2026-04-09T10:00:00Z",
        direction: "outbound",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MessageComposer />);
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect((textarea as HTMLTextAreaElement).value).toBe("");
    });

    vi.unstubAllGlobals();
  });
});

// ── BookAppointmentSheet ─────────────────────────────────────────────────────
import { BookAppointmentSheet } from "../_components/BookAppointmentSheet";

describe("BookAppointmentSheet", () => {
  it("renders nothing when closed", () => {
    render(<BookAppointmentSheet open={false} onClose={vi.fn()} pillar="Clinics" />);
    expect(screen.queryByText("Book Appointment")).not.toBeInTheDocument();
  });

  it("renders title when open", () => {
    render(<BookAppointmentSheet open={true} onClose={vi.fn()} pillar="Clinics" />);
    expect(screen.getByText("Book Appointment")).toBeInTheDocument();
  });

  it("renders the pillar name in the form", () => {
    render(<BookAppointmentSheet open={true} onClose={vi.fn()} pillar="Diagnostics" />);
    expect(screen.getByText(/Diagnostics/i)).toBeInTheDocument();
  });

  it("renders a confirm button", () => {
    render(<BookAppointmentSheet open={true} onClose={vi.fn()} pillar="Home Care" />);
    expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
  });

  it("calls onClose when cancel is tapped", () => {
    const onClose = vi.fn();
    render(<BookAppointmentSheet open={true} onClose={onClose} pillar="Clinics" />);
    const cancelBtn = screen.getByRole("button", { name: /cancel/i });
    fireEvent.click(cancelBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
