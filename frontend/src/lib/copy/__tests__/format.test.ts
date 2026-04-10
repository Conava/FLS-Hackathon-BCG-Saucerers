import { describe, it, expect } from "vitest";
import {
  formatScore,
  formatDelta,
  formatDate,
  formatRelativeTime,
  formatMacro,
} from "../format";

// ---------------------------------------------------------------------------
// formatScore
// ---------------------------------------------------------------------------
describe("formatScore", () => {
  it("rounds a float to nearest integer string", () => {
    expect(formatScore(82.6)).toBe("83");
    expect(formatScore(82.4)).toBe("82");
  });

  it("returns '0' for zero", () => {
    expect(formatScore(0)).toBe("0");
  });

  it("returns '100' for 100", () => {
    expect(formatScore(100)).toBe("100");
  });

  it("handles negative values (edge case)", () => {
    expect(formatScore(-1)).toBe("-1");
  });
});

// ---------------------------------------------------------------------------
// formatDelta
// ---------------------------------------------------------------------------
describe("formatDelta", () => {
  it("prefixes positive values with +", () => {
    expect(formatDelta(2.5)).toBe("+2.5");
  });

  it("prefixes negative values with -", () => {
    expect(formatDelta(-1.0)).toBe("-1.0");
  });

  it("shows zero as +0.0", () => {
    expect(formatDelta(0)).toBe("+0.0");
  });

  it("respects custom decimal places", () => {
    expect(formatDelta(3.14159, 2)).toBe("+3.14");
    expect(formatDelta(-3.14159, 0)).toBe("-3");
  });
});

// ---------------------------------------------------------------------------
// formatDate
// ---------------------------------------------------------------------------
describe("formatDate", () => {
  it("formats a Date object", () => {
    const d = new Date("2026-04-09T00:00:00Z");
    const result = formatDate(d, "en-GB");
    expect(result).toMatch(/Apr/);
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/9/);
  });

  it("accepts an ISO string", () => {
    const result = formatDate("2026-01-01T00:00:00Z", "en-GB");
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/Jan/);
  });
});

// ---------------------------------------------------------------------------
// formatRelativeTime
// ---------------------------------------------------------------------------
describe("formatRelativeTime", () => {
  const now = new Date("2026-04-09T12:00:00Z");

  it("returns 'just now' for < 1 minute ago", () => {
    const recent = new Date("2026-04-09T11:59:45Z");
    expect(formatRelativeTime(recent, now)).toBe("just now");
  });

  it("returns minutes ago for < 1 hour", () => {
    const thirtyMinAgo = new Date("2026-04-09T11:30:00Z");
    const result = formatRelativeTime(thirtyMinAgo, now);
    expect(result).toMatch(/30 minutes ago/);
  });

  it("returns hours ago for < 1 day", () => {
    const twoHoursAgo = new Date("2026-04-09T10:00:00Z");
    const result = formatRelativeTime(twoHoursAgo, now);
    expect(result).toMatch(/2 hours ago/);
  });

  it("returns 'yesterday' for ~1 day ago", () => {
    const yesterday = new Date("2026-04-08T12:00:00Z");
    const result = formatRelativeTime(yesterday, now);
    expect(result).toMatch(/yesterday/i);
  });

  it("returns days ago for < 30 days", () => {
    const fiveDaysAgo = new Date("2026-04-04T12:00:00Z");
    const result = formatRelativeTime(fiveDaysAgo, now);
    expect(result).toMatch(/5 days ago/);
  });

  it("falls back to formatted date for >= 30 days", () => {
    const longAgo = new Date("2026-01-01T00:00:00Z");
    const result = formatRelativeTime(longAgo, now);
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/Jan/);
  });

  it("accepts an ISO string", () => {
    const result = formatRelativeTime("2026-04-09T11:59:45Z", now);
    expect(result).toBe("just now");
  });
});

// ---------------------------------------------------------------------------
// formatMacro
// ---------------------------------------------------------------------------
describe("formatMacro", () => {
  it("rounds to integer with default unit 'g'", () => {
    expect(formatMacro(52.7)).toBe("53 g");
  });

  it("accepts custom unit", () => {
    expect(formatMacro(2000, "kcal")).toBe("2000 kcal");
  });

  it("rounds fractional grams", () => {
    expect(formatMacro(0.4)).toBe("0 g");
    expect(formatMacro(0.6)).toBe("1 g");
  });
});
