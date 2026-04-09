/**
 * POST /api/auth/logout
 *
 * Clears the patient_id httpOnly cookie and returns 200 OK.
 */

import { NextResponse } from "next/server";
import { clearPatientId } from "@/lib/auth/session";

export async function POST(): Promise<NextResponse> {
  await clearPatientId();
  return NextResponse.json({ ok: true }, { status: 200 });
}
