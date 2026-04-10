/**
 * Focused security tests for the /api/proxy/[...path] route handler.
 *
 * Tests:
 * - Path traversal via literal `..` segment returns 400
 * - Path traversal via percent-encoded `%2e%2e` returns 400
 * - Cookie header from the incoming request is NOT forwarded to upstream fetch
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

// ---------------------------------------------------------------------------
// Module-level mocks — must be hoisted before dynamic imports of the route
// ---------------------------------------------------------------------------

// Mock next/headers so the route sees a valid patient_id cookie.
// The factory must be synchronous (no vi.fn() calls that capture state).
vi.mock("next/headers", () => {
  const cookieStore = {
    get: (name: string) =>
      name === "patient_id" ? { value: "patient-123" } : undefined,
  };
  return {
    cookies: () => Promise.resolve(cookieStore),
  };
});

// ---------------------------------------------------------------------------
// Import the route handler under test
// ---------------------------------------------------------------------------
import { GET } from "../[...path]/route";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal NextRequest pointing at the proxy route. */
function makeRequest(
  pathSegments: string[],
  extraHeaders: Record<string, string> = {},
): NextRequest {
  const url = `http://localhost:3000/api/proxy/${pathSegments.join("/")}`;
  return new NextRequest(url, {
    method: "GET",
    headers: extraHeaders,
  });
}

/** Build the context object that Next.js passes alongside the request. */
function makeContext(pathSegments: string[]) {
  return {
    params: Promise.resolve({ path: pathSegments }),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("proxy route — path traversal rejection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns 400 when path contains a literal `..` segment", async () => {
    const req = makeRequest(["..", "foo"]);
    const ctx = makeContext(["..", "foo"]);

    const res = await GET(req, ctx);

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body).toEqual({ error: "Invalid path" });
  });

  it("returns 400 when path contains a percent-encoded `..` (%2e%2e)", async () => {
    // The raw segment as it arrives from the URL is the encoded form.
    // validateSegment must decode and reject it.
    const req = makeRequest(["%2e%2e", "foo"]);
    const ctx = makeContext(["%2e%2e", "foo"]);

    const res = await GET(req, ctx);

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body).toEqual({ error: "Invalid path" });
  });
});

describe("proxy route — header leakage prevention", () => {
  it("does NOT forward the cookie header to the upstream fetch", async () => {
    // Arrange: spy on global fetch so we can inspect the forwarded headers.
    // Return a minimal 200 response to let the handler complete.
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", mockFetch);

    const req = makeRequest(["metrics"], {
      cookie: "patient_id=patient-123; session=abc",
      "content-type": "application/json",
    });
    const ctx = makeContext(["metrics"]);

    await GET(req, ctx);

    // Verify fetch was called
    expect(mockFetch).toHaveBeenCalledOnce();

    // Inspect the Headers object passed as the second argument's `headers`
    const [, fetchInit] = mockFetch.mock.calls[0] as [string, RequestInit];
    const forwardedHeaders = fetchInit.headers as Headers;

    // The cookie header must have been stripped
    expect(forwardedHeaders.get("cookie")).toBeNull();

    // Safe headers should still be forwarded
    expect(forwardedHeaders.get("content-type")).toBe("application/json");
  });
});
