import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import TabBar from "@/components/shell/TabBar";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

describe("TabBar", () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockReturnValue("/today");
  });

  it("renders 6 navigation links (5 tabs + Me)", () => {
    render(<TabBar />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(6);
  });

  it("renders all expected tab labels", () => {
    render(<TabBar />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Coach")).toBeInTheDocument();
    expect(screen.getByText("Records")).toBeInTheDocument();
    expect(screen.getByText("Insights")).toBeInTheDocument();
    expect(screen.getByText("Care")).toBeInTheDocument();
    expect(screen.getByText("Me")).toBeInTheDocument();
  });

  it("marks Today tab as active when pathname is /today", () => {
    vi.mocked(usePathname).mockReturnValue("/today");
    render(<TabBar />);
    const todayLink = screen.getByRole("link", { name: /today/i });
    expect(todayLink).toHaveAttribute("aria-current", "page");
  });

  it("marks Coach tab as active when pathname is /coach", () => {
    vi.mocked(usePathname).mockReturnValue("/coach");
    render(<TabBar />);
    const coachLink = screen.getByRole("link", { name: /coach/i });
    expect(coachLink).toHaveAttribute("aria-current", "page");
  });

  it("marks other tabs as inactive when Today is active", () => {
    vi.mocked(usePathname).mockReturnValue("/today");
    render(<TabBar />);
    const coachLink = screen.getByRole("link", { name: /coach/i });
    expect(coachLink).not.toHaveAttribute("aria-current", "page");
  });

  it("renders as a nav element with role tablist", () => {
    render(<TabBar />);
    expect(screen.getByRole("tablist")).toBeInTheDocument();
  });
});
