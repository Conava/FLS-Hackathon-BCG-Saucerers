import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import Home from "@/app/page";

// next/navigation redirect throws a special error in tests
vi.mock("next/navigation", () => ({
  redirect: vi.fn((path: string) => {
    throw new Error(`NEXT_REDIRECT:${path}`);
  }),
}));

describe("Home page", () => {
  it("redirects to /today", () => {
    expect(() => render(<Home />)).toThrow("NEXT_REDIRECT:/today");
  });
});
