/**
 * POST /api/auth/login
 *
 * Demo auth endpoint. Accepts { patient_id: string }, validates the format,
 * sets an httpOnly cookie, and returns 200 OK.
 *
 * patient_id is accepted as:
 *   - UUID v4 (e.g. "550e8400-e29b-41d4-a716-446655440000")
 *   - pt-xxx  (e.g. "pt-0199", "pt-abc")
 *   - PTNNNN  (e.g. "PT0282") — uppercase format from the backend CSV data
 */

import { NextRequest, NextResponse } from "next/server";
import { setPatientId } from "@/lib/auth/session";

/**
 * Validate patient ID format.
 * Accepts UUID v4, pt-xxx, or PTNNNN patterns.
 */
function isValidPatientId(id: string): boolean {
  // UUID v4
  const uuidV4 =
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  // pt-xxx pattern (demo format)
  const ptDash = /^pt-[a-z0-9]+$/i;
  // PTNNNN pattern (backend CSV format, e.g. PT0282)
  const ptUppercase = /^PT\d+$/;

  return uuidV4.test(id) || ptDash.test(id) || ptUppercase.test(id);
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 },
    );
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("patient_id" in body) ||
    typeof (body as Record<string, unknown>).patient_id !== "string"
  ) {
    return NextResponse.json(
      { error: "patient_id is required and must be a string" },
      { status: 400 },
    );
  }

  const patientId = (body as { patient_id: string }).patient_id.trim();

  if (!isValidPatientId(patientId)) {
    return NextResponse.json(
      { error: "Invalid patient_id format. Expected UUID, pt-xxx, or PTnnnn." },
      { status: 400 },
    );
  }

  await setPatientId(patientId);

  return NextResponse.json({ ok: true }, { status: 200 });
}
