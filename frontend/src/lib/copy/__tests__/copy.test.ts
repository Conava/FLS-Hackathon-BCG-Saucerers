import { describe, it, expect } from "vitest";
import { COPY, AI_DISCLOSURE } from "../copy";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Recursively collect every string value from a (potentially deeply nested)
 * object. Skips functions (e.g. the greeting formatter).
 */
function collectStrings(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (typeof value === "function") return [];
  if (Array.isArray(value)) return value.flatMap(collectStrings);
  if (value !== null && typeof value === "object") {
    return Object.values(value as Record<string, unknown>).flatMap(
      collectStrings
    );
  }
  return [];
}

// ---------------------------------------------------------------------------
// Banned vocabulary — must never appear in any copy string
// ---------------------------------------------------------------------------

const BANNED_VERBS = [
  "diagnose",
  "diagnosis",
  "treat",
  "treatment",
  "cure",
  "cures",
  "heal",
  "heals",
  "prevent disease",
] as const;

/**
 * Build a word-boundary regex for the given term.
 * Multi-word phrases (e.g. "prevent disease") use a space-aware boundary.
 */
function bannedPattern(term: string): RegExp {
  // For multi-word phrases just match literally (case-insensitive)
  if (term.includes(" ")) {
    return new RegExp(term, "i");
  }
  return new RegExp(`\\b${term}\\b`, "i");
}

describe("COPY — wellness framing compliance", () => {
  const allStrings = collectStrings(COPY);

  it("exports at least one string per top-level section", () => {
    expect(allStrings.length).toBeGreaterThan(0);
  });

  for (const verb of BANNED_VERBS) {
    it(`contains no banned verb: "${verb}"`, () => {
      const pattern = bannedPattern(verb);
      const violations = allStrings.filter((s) => pattern.test(s));
      expect(
        violations,
        `Found banned term "${verb}" in copy strings: ${violations.join(", ")}`
      ).toHaveLength(0);
    });
  }
});

// ---------------------------------------------------------------------------
// AI_DISCLOSURE
// ---------------------------------------------------------------------------

describe("AI_DISCLOSURE", () => {
  it("is a non-empty string", () => {
    expect(typeof AI_DISCLOSURE).toBe("string");
    expect(AI_DISCLOSURE.length).toBeGreaterThan(0);
  });

  it("mentions AI", () => {
    expect(AI_DISCLOSURE).toMatch(/AI/i);
  });

  it("mentions wellness or guidance", () => {
    expect(AI_DISCLOSURE).toMatch(/wellness|guidance/i);
  });

  it("does not use banned verbs", () => {
    for (const verb of BANNED_VERBS) {
      expect(AI_DISCLOSURE).not.toMatch(bannedPattern(verb));
    }
  });
});

// ---------------------------------------------------------------------------
// Structural shape checks
// ---------------------------------------------------------------------------

describe("COPY structure", () => {
  it("has tabBar labels for all six tabs", () => {
    const labels = Object.values(COPY.tabBar);
    expect(labels).toHaveLength(6);
    labels.forEach((l) => expect(typeof l).toBe("string"));
  });

  it("has four onboarding steps", () => {
    expect(COPY.onboarding.steps).toHaveLength(4);
  });

  it("every onboarding step has title and body", () => {
    COPY.onboarding.steps.forEach((step) => {
      expect(typeof step.title).toBe("string");
      expect(typeof step.body).toBe("string");
    });
  });

  it("has disclosure string in coach section", () => {
    expect(typeof COPY.coach.disclosure).toBe("string");
    expect(COPY.coach.disclosure.length).toBeGreaterThan(0);
  });

  it("has disclosure string in records section", () => {
    expect(typeof COPY.records.disclosure).toBe("string");
    expect(COPY.records.disclosure.length).toBeGreaterThan(0);
  });

  it("has gdpr section under me", () => {
    expect(COPY.me.gdpr).toBeDefined();
    expect(typeof COPY.me.gdpr.exportData).toBe("string");
    expect(typeof COPY.me.gdpr.deleteAccount).toBe("string");
  });

  it("insights dimensions covers expected keys", () => {
    const dims = Object.keys(COPY.insights.dimensions);
    expect(dims).toContain("sleep");
    expect(dims).toContain("activity");
    expect(dims).toContain("nutrition");
    expect(dims).toContain("longevity");
  });

  it("care pillars covers expected keys", () => {
    const pillars = Object.keys(COPY.care.pillars);
    expect(pillars).toContain("movement");
    expect(pillars).toContain("rest");
    expect(pillars).toContain("nourishment");
  });
});
