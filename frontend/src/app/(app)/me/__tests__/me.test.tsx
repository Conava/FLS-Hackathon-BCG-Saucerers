import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import GdprActions from "../_components/GdprActions";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock URL.createObjectURL / revokeObjectURL (not available in jsdom)
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
global.URL.revokeObjectURL = vi.fn();

// Mock document.createElement to intercept anchor click for download
const originalCreateElement = document.createElement.bind(document);
const mockAnchorClick = vi.fn();
vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
  if (tag === "a") {
    const el = originalCreateElement("a");
    el.click = mockAnchorClick;
    return el;
  }
  return originalCreateElement(tag);
});

// ---------------------------------------------------------------------------

describe("GdprActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  it("renders Export and Delete buttons", () => {
    render(<GdprActions />);
    expect(
      screen.getByRole("button", { name: /export my data/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /delete my account/i }),
    ).toBeInTheDocument();
  });

  it("calls gdpr/export endpoint and triggers download on Export click", async () => {
    const exportPayload = {
      patient_id: "PT0199",
      patient: { patient_id: "PT0199", name: "Rebecca", age: 34, country: "DE" },
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => exportPayload,
    });

    render(<GdprActions />);
    fireEvent.click(screen.getByRole("button", { name: /export my data/i }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/proxy/gdpr/export",
        expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) }),
      );
    });

    await waitFor(() => {
      expect(global.URL.createObjectURL).toHaveBeenCalled();
      expect(mockAnchorClick).toHaveBeenCalled();
    });
  });

  it("shows loading state while export is in progress", async () => {
    let resolveExport!: (v: unknown) => void;
    const exportPromise = new Promise((res) => { resolveExport = res; });

    mockFetch.mockReturnValueOnce(exportPromise);

    render(<GdprActions />);
    fireEvent.click(screen.getByRole("button", { name: /export my data/i }));

    // Button should show loading text
    expect(screen.getByRole("button", { name: /exporting/i })).toBeInTheDocument();

    // Resolve to avoid act warnings
    await act(async () => {
      resolveExport({ ok: true, json: async () => ({ patient_id: "PT0199" }) });
      await exportPromise;
    });
  });

  it("opens delete confirmation dialog on Delete click", () => {
    render(<GdprActions />);
    fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));
    // Dialog should be visible with confirmation text
    expect(screen.getByText(/permanently remove/i)).toBeInTheDocument();
  });

  it("calls gdpr delete endpoint and redirects to /login after confirmation", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "scheduled", status: "scheduled" }),
    });
    // Second fetch for logout
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    render(<GdprActions />);

    // Open dialog
    fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));

    // Confirm deletion
    const confirmBtn = screen.getByRole("button", { name: /confirm delete/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/proxy/gdpr",
        expect.objectContaining({ method: "DELETE" }),
      );
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });
});
