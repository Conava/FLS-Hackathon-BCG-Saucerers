/**
 * Next.js Route Handler: /api/proxy/[...path]
 *
 * Rewrites requests from /api/proxy/foo/bar →
 *   ${BACKEND_URL}/v1/patients/${patient_id}/foo/bar
 *
 * Security:
 * - Reads patient_id from httpOnly `patient_id` cookie (set by auth routes).
 * - Returns 401 if cookie is absent.
 * - Never exposes the backend URL or patient_id to the client.
 *
 * SSE pass-through:
 * - For text/event-stream responses the upstream ReadableStream is passed
 *   through directly without buffering.
 *
 * Supported methods: GET, POST, PUT, DELETE.
 *
 * Next.js 15: route handler params are a Promise — always await.
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.BACKEND_URL ?? "http://localhost:8000";

/**
 * Headers that must not be forwarded to the upstream backend.
 * Includes hop-by-hop headers, auth/session headers, and routing headers
 * that could leak caller identity or be used for header injection.
 */
const DENIED_HEADERS = new Set([
  // Standard hop-by-hop headers
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "proxy-authorization",
  "proxy-authenticate",
  // Auth/session — must never reach upstream (backend uses its own auth)
  "cookie",
  "authorization",
  // Internal routing headers that must not be spoofed
  "host",
  "x-patient-id",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-proto",
]);

/** Build a filtered copy of the incoming headers for forwarding. */
function forwardHeaders(incoming: Headers): Headers {
  const out = new Headers();
  incoming.forEach((value, key) => {
    if (!DENIED_HEADERS.has(key.toLowerCase())) {
      out.set(key, value);
    }
  });
  return out;
}

/**
 * Validate a single URL path segment.
 *
 * Rejects empty segments, dot-traversal (. and ..), and any segment that
 * contains a path separator or NUL byte after decoding. This prevents
 * path traversal attacks via the catch-all [...path] parameter.
 */
function validateSegment(raw: string): boolean {
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return false;
  }
  if (decoded.length === 0) return false;
  if (decoded === "." || decoded === "..") return false;
  if (decoded.includes("/") || decoded.includes("\\") || decoded.includes("\0")) return false;
  return true;
}

async function handleRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse | Response> {
  // 1. Read the patient_id cookie — 401 if absent
  const store = await cookies();
  const patientId = store.get("patient_id")?.value;
  if (!patientId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // 2. Resolve and validate the path segments
  const { path } = await context.params;

  // Reject any segment that is empty, dot-traversal, or contains separators
  for (const seg of path) {
    if (!validateSegment(seg)) {
      return NextResponse.json({ error: "Invalid path" }, { status: 400 });
    }
  }

  const segments = path.join("/");

  // 3. Build the upstream URL, preserving any query string
  const incomingUrl = new URL(request.url);
  const upstreamUrl = new URL(
    `/v1/patients/${patientId}/${segments}${incomingUrl.search}`,
    BACKEND_URL,
  );

  // Guard: ensure the resolved pathname is strictly scoped to this patient.
  // URL normalization could theoretically collapse the path — this is the
  // last line of defence before the request leaves the proxy.
  const expectedPrefix = `/v1/patients/${patientId}/`;
  if (!upstreamUrl.pathname.startsWith(expectedPrefix)) {
    return NextResponse.json({ error: "Invalid path" }, { status: 400 });
  }

  // 4. Forward headers, stripping denied headers
  const headers = forwardHeaders(request.headers);

  // 5. Build fetch init — include body for non-GET/HEAD methods
  const method = request.method;
  const hasBody = !["GET", "HEAD"].includes(method);

  const init: RequestInit = {
    method,
    headers,
    // Pass the raw body stream through for POST/PUT/DELETE
    body: hasBody ? request.body : undefined,
    // Disable body consumption check — we pass the ReadableStream through
    // @ts-expect-error — duplex is required for streaming request bodies in Node 18+
    duplex: hasBody ? "half" : undefined,
  };

  // 6. Forward to the backend
  let upstream: globalThis.Response;
  try {
    upstream = await fetch(upstreamUrl.toString(), init);
  } catch (err) {
    console.error("[proxy] upstream fetch error", err);
    return NextResponse.json(
      { error: "Backend unreachable" },
      { status: 502 },
    );
  }

  // 7. Build response headers, preserving content-type from upstream
  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!DENIED_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  const contentType = upstream.headers.get("content-type") ?? "";

  // 8. For SSE: pass the ReadableStream through directly (no buffering)
  if (contentType.includes("text/event-stream")) {
    responseHeaders.set("Content-Type", "text/event-stream");
    responseHeaders.set("Cache-Control", "no-cache");
    responseHeaders.set("X-Accel-Buffering", "no");

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  }

  // 9. For all other responses: stream body through
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const DELETE = handleRequest;
