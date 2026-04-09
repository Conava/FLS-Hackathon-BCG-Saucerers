/**
 * Server-side session helpers for the demo auth layer.
 *
 * Reads and writes the httpOnly `patient_id` cookie via next/headers.
 * All three helpers are server-only (they use `cookies()` from next/headers).
 *
 * Next.js 15: `cookies()` returns a Promise — always await it.
 */

import { cookies } from "next/headers";

const COOKIE_NAME = "patient_id";

/** Cookie options shared across set/clear operations. */
function cookieOptions(maxAge?: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    path: "/",
    secure: process.env.NODE_ENV === "production",
    ...(maxAge !== undefined ? { maxAge } : {}),
  };
}

/**
 * Read the patient_id from the httpOnly cookie.
 * Returns `undefined` when the cookie is absent.
 */
export async function getPatientId(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value;
}

/**
 * Set the patient_id httpOnly cookie.
 * Expires after 30 days (demo session length).
 */
export async function setPatientId(id: string): Promise<void> {
  const store = await cookies();
  store.set(COOKIE_NAME, id, cookieOptions(60 * 60 * 24 * 30));
}

/**
 * Clear the patient_id cookie (logout).
 */
export async function clearPatientId(): Promise<void> {
  const store = await cookies();
  store.set(COOKIE_NAME, "", cookieOptions(0));
}
