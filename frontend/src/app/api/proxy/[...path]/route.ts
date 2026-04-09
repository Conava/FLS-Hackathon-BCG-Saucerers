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

/** Headers that must not be forwarded to the upstream backend. */
const HOP_BY_HOP = new Set([
  "host",
  "connection",
  "keep-alive",
  "transfer-encoding",
  "te",
  "trailer",
  "upgrade",
  "proxy-authorization",
  "proxy-authenticate",
]);

/** Build a filtered copy of the incoming headers for forwarding. */
function forwardHeaders(incoming: Headers): Headers {
  const out = new Headers();
  incoming.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      out.set(key, value);
    }
  });
  return out;
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

  // 2. Resolve the path segments
  const { path } = await context.params;
  const segments = path.join("/");

  // 3. Build the upstream URL, preserving any query string
  const incomingUrl = new URL(request.url);
  const upstreamUrl = new URL(
    `/v1/patients/${patientId}/${segments}${incomingUrl.search}`,
    BACKEND_URL,
  );

  // 4. Forward headers, stripping hop-by-hop headers
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
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
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
