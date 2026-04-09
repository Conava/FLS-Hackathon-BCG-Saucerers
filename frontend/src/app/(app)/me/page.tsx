/**
 * Me screen — profile, data sources, consents, GDPR actions, logout.
 *
 * Server Component: fetches patient profile from the backend.
 * GDPR export/delete and logout require client-side handlers — delegated to
 * `_components/GdprActions.tsx` and `_components/LogoutButton.tsx`.
 *
 * Stack: Next.js 15 App Router, Tailwind v4.
 */

import Link from "next/link";
import { COPY } from "@/lib/copy/copy";
import { getPatientProfile } from "@/lib/api/client";
import { Switch } from "@/components/ui/switch";
import GdprActions from "./_components/GdprActions";
import LogoutButton from "./_components/LogoutButton";

// ---------------------------------------------------------------------------
// Static data sources list — visual only, toggled client-side
// ---------------------------------------------------------------------------
const DATA_SOURCES = [
  { id: "apple-health", label: "Apple Health" },
  { id: "withings", label: "Withings" },
  { id: "oura", label: "Oura Ring" },
  { id: "ehr", label: "Electronic Health Record" },
  { id: "lifestyle", label: "Lifestyle Survey" },
];

// ---------------------------------------------------------------------------
// Static consent list — read-only
// ---------------------------------------------------------------------------
const CONSENTS = [
  "Processing of health data for wellness insights",
  "Sharing anonymised data for service improvement",
  "AI-generated wellness recommendations",
  "Email notifications for wellness milestones",
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Me page — fetches patient profile server-side, renders profile header,
 * data sources, consents, privacy/GDPR section, and logout.
 */
export default async function MePage() {
  // Gracefully handle missing backend in dev
  let profile: {
    patient_id: string;
    name: string;
    age: number;
    country: string;
  } | null = null;
  try {
    profile = await getPatientProfile();
  } catch {
    // Silently degrade in demo environments where backend may not be running
  }

  const initials = profile?.name
    ? profile.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  return (
    <div
      className="min-h-dvh pb-8"
      style={{ backgroundColor: "var(--color-bg)" }}
    >
      {/* Page header */}
      <header
        className="px-5 pt-12 pb-6"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <h1
          className="text-2xl font-bold"
          style={{ color: "var(--color-ink)" }}
        >
          {COPY.me.title}
        </h1>
      </header>

      <div className="px-5 space-y-8 pt-6">
        {/* Profile header */}
        <section aria-label="Profile">
          <div className="flex items-center gap-4">
            {/* Avatar placeholder */}
            <div
              className="flex h-16 w-16 items-center justify-center rounded-full text-xl font-bold"
              style={{
                backgroundColor: "var(--color-accent-lt)",
                color: "var(--color-accent)",
              }}
              aria-hidden="true"
            >
              {initials}
            </div>
            <div>
              <p
                className="text-xl font-semibold"
                style={{ color: "var(--color-ink)" }}
              >
                {profile?.name ?? "\u2014"}
              </p>
              <p
                className="text-sm"
                style={{ color: "var(--color-ink-3)" }}
              >
                {profile?.patient_id ?? "\u2014"}
              </p>
            </div>
          </div>

          {/* Retake survey */}
          <div className="mt-4">
            <Link
              href="/onboarding"
              className="text-sm font-medium underline-offset-2 hover:underline"
              style={{ color: "var(--color-accent)" }}
            >
              Retake survey
            </Link>
          </div>
        </section>

        {/* Data sources */}
        <section aria-label="Data sources">
          <h2
            className="mb-3 text-xs font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-ink-4)" }}
          >
            Data Sources
          </h2>
          <div
            className="rounded-xl overflow-hidden"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            {DATA_SOURCES.map((src, idx) => (
              <div
                key={src.id}
                className="flex items-center justify-between px-4 py-3"
                style={{
                  borderTop:
                    idx > 0 ? "1px solid var(--color-border)" : undefined,
                }}
              >
                <span
                  className="text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  {src.label}
                </span>
                {/* Visual-only toggle — defaultChecked for first two in demo */}
                <Switch
                  defaultChecked={idx < 2}
                  aria-label={`Toggle ${src.label}`}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Consent list */}
        <section aria-label="Consents">
          <h2
            className="mb-3 text-xs font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-ink-4)" }}
          >
            {COPY.me.sections.about}
          </h2>
          <div
            className="rounded-xl overflow-hidden"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            {CONSENTS.map((item, idx) => (
              <div
                key={item}
                className="flex items-start gap-3 px-4 py-3"
                style={{
                  borderTop:
                    idx > 0 ? "1px solid var(--color-border)" : undefined,
                }}
              >
                <span
                  className="mt-0.5 text-sm"
                  style={{ color: "var(--color-accent)" }}
                  aria-hidden="true"
                >
                  &#10003;
                </span>
                <span
                  className="text-sm"
                  style={{ color: "var(--color-ink-2)" }}
                >
                  {item}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Notifications (stub) */}
        <section aria-label="Notifications">
          <h2
            className="mb-3 text-xs font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-ink-4)" }}
          >
            {COPY.me.sections.notifications}
          </h2>
          <div
            className="rounded-xl px-4 py-3"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div className="flex items-center justify-between">
              <span
                className="text-sm font-medium"
                style={{ color: "var(--color-ink)" }}
              >
                Push notifications
              </span>
              <Switch defaultChecked aria-label="Toggle push notifications" />
            </div>
          </div>
        </section>

        {/* Privacy & GDPR */}
        <section aria-label="Privacy and data">
          <h2
            className="mb-3 text-xs font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-ink-4)" }}
          >
            {COPY.me.sections.privacy}
          </h2>
          <div
            className="rounded-xl p-4"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            <h3
              className="mb-1 font-semibold"
              style={{ color: "var(--color-ink)" }}
            >
              {COPY.me.gdpr.heading}
            </h3>
            <GdprActions />
          </div>
        </section>

        {/* Logout */}
        <section aria-label="Sign out">
          <LogoutButton />
        </section>
      </div>
    </div>
  );
}
