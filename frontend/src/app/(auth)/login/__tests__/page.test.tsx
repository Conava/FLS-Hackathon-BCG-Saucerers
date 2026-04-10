import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "../page";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page heading and patient ID input", () => {
    render(<LoginPage />);
    expect(
      screen.getByRole("heading", { name: /welcome back/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/pt-001 or pt0199/i),
    ).toBeInTheDocument();
  });

  it("renders the sign in button", () => {
    render(<LoginPage />);
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("renders demo patient shortcut buttons", () => {
    render(<LoginPage />);
    // At least 2 demo shortcuts should be rendered
    const demoButtons = screen
      .getAllByRole("button")
      .filter((btn) => btn.getAttribute("data-demo") === "true");
    expect(demoButtons.length).toBeGreaterThanOrEqual(2);
  });

  it("autofills patient ID when a demo shortcut is clicked", () => {
    render(<LoginPage />);
    const demoButtons = screen
      .getAllByRole("button")
      .filter((btn) => btn.getAttribute("data-demo") === "true");
    const firstDemo = demoButtons[0];
    expect(firstDemo).toBeDefined();
    fireEvent.click(firstDemo!);
    const input = screen.getByPlaceholderText(
      /pt-001 or pt0199/i,
    ) as HTMLInputElement;
    expect(input.value).not.toBe("");
  });

  it("shows inline error when API returns 400", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        error: "Invalid patient_id format.",
      }),
    });

    render(<LoginPage />);
    const input = screen.getByPlaceholderText(/pt-001 or pt0199/i);
    fireEvent.change(input, { target: { value: "bad-id!!!" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("redirects to /today on successful login", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true }),
    });

    render(<LoginPage />);
    const input = screen.getByPlaceholderText(/pt-001 or pt0199/i);
    fireEvent.change(input, { target: { value: "PT0199" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/today");
    });
  });
});
