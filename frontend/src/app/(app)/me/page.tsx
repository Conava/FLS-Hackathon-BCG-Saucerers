/**
 * Me screen — rebuilt to match the mockup profile sheet treatment.
 *
 * Sections (in order):
 *  1. Header — h1 "Me" + subtitle
 *  2. Profile card — avatar, name, bio
 *  3. Stat cards grid — streak, WALR, vitality
 *  4. Quick links list — retake survey, data sources, privacy, notifications,
 *     refer a friend, sign out
 *  5. Data sources section (anchor: #data-sources)
 *  6. Consents section (anchor: #consents)
 *  7. Privacy & GDPR actions (anchor: #privacy)
 *
 * Server Component: fetches patient profile.
 * Client interactivity delegated to GdprActions and LogoutButton.
 *
 * Stack: Next.js 15 App Router, Tailwind v4.
 */

import Link from "next/link";
import { getPatientProfile } from "@/lib/api/client";
import { Switch } from "@/components/ui/switch";
import GdprActions from "./_components/GdprActions";
import LogoutButton from "./_components/LogoutButton";
import ScreenFrame from "@/components/shell/ScreenFrame";
import { PageHeader } from "@/components/shell/PageHeader";

// ---------------------------------------------------------------------------
// Demo stats — tagged // demo until backend exposes these fields
// ---------------------------------------------------------------------------
const DEMO_STREAK = 6; // demo
const DEMO_WALR = 18; // demo
const DEMO_VITALITY = 68; // demo

// ---------------------------------------------------------------------------
// Static data sources list — visual only
// ---------------------------------------------------------------------------
const DATA_SOURCES = [
  { id: "apple-health", label: "Apple Health" },
  { id: "withings", label: "Withings" },
  { id: "oura", label: "Oura Ring" },
  { id: "ehr", label: "Electronic Health Record" },
  { id: "lifestyle", label: "Lifestyle Survey" },
];

// ---------------------------------------------------------------------------
// Static consent list — read-only with checkmarks
// ---------------------------------------------------------------------------
const CONSENTS = [
  "Processing of health data for wellness insights",
  "Sharing anonymised data for service improvement",
  "AI-generated wellness recommendations",
  "Email notifications for wellness milestones",
];

// ---------------------------------------------------------------------------
// RowList container — bordered rounded card for grouped rows
// ---------------------------------------------------------------------------
function RowList({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        border: "1px solid var(--color-border)",
        background: "var(--color-surface)",
      }}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SectionHeading
// ---------------------------------------------------------------------------
function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="mb-3 text-xs font-semibold uppercase tracking-wider"
      style={{ color: "var(--color-ink-4)" }}
    >
      {children}
    </h2>
  );
}

// ---------------------------------------------------------------------------
// ChevronIcon
// ---------------------------------------------------------------------------
function ChevronIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
      style={{ color: "var(--color-ink-4)", flexShrink: 0 }}
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Me page — profile card, stats, quick links, data sources, consents, privacy.
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

  // Derive initials
  const initials = profile?.name
    ? profile.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  // Bio line: age · city · Longevity+ member
  const bioParts: string[] = [];
  if (profile?.age) bioParts.push(String(profile.age));
  if (profile?.country) bioParts.push(profile.country);
  bioParts.push("Longevity+ member");
  const bioLine = bioParts.join(" · ");

  // Row divider style — reused across quick-link rows
  const rowDivider: React.CSSProperties = {
    borderTop: "1px solid var(--color-border)",
  };

  return (
    <ScreenFrame>
      {/* ── 1. Header ─────────────────────────────────────────────────────── */}
      <PageHeader
        title={profile?.name ? (profile.name.split(" ")[0] ?? "Me") : "Me"}
        subtitle="Your profile and data controls"
        mb={16}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* ── 2. Profile card ───────────────────────────────────────────── */}
        <section aria-label="Profile">
          <div
            className="rounded-xl p-5 flex flex-col items-center text-center"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            {/* Avatar 48×48 — accent background, white initials */}
            <div
              className="flex h-12 w-12 items-center justify-center rounded-full text-base font-extrabold"
              style={{ backgroundColor: "var(--color-accent)", color: "#fff" }}
              aria-hidden="true"
            >
              {initials}
            </div>

            {/* Name — 16px / 800 */}
            <p
              className="mt-3 text-base font-extrabold"
              style={{ color: "var(--color-ink)" }}
            >
              {profile?.name ?? "—"}
            </p>

            {/* Bio — age · city · Longevity+ member — 12px / ink-3 */}
            <p className="mt-1 text-xs" style={{ color: "var(--color-ink-3)" }}>
              {bioLine}
            </p>
          </div>
        </section>

        {/* ── 3. Stat cards grid — 3 columns ────────────────────────────── */}
        <section aria-label="Your stats">
          <div className="grid grid-cols-3 gap-2">
            {/* demo values — replace when backend exposes streak/WALR */}
            {[
              { value: DEMO_STREAK, label: "Day streak" },
              { value: DEMO_WALR, label: "WALR (weekly)" },
              { value: DEMO_VITALITY, label: "Vitality" },
            ].map(({ value, label }) => (
              <div
                key={label}
                className="rounded-xl p-3 text-center"
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {/* Value — 20px / 800 / ink */}
                <div
                  className="text-xl font-extrabold"
                  style={{ color: "var(--color-ink)" }}
                >
                  {value}
                </div>
                {/* Label — 10px / uppercase / ink-3 */}
                <div
                  className="mt-0.5 text-[10px] font-semibold uppercase tracking-wide"
                  style={{ color: "var(--color-ink-3)" }}
                >
                  {label}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── 4. Quick links ────────────────────────────────────────────── */}
        <section aria-label="Quick links">
          <RowList>
            {/* Retake lifestyle survey → /onboarding */}
            <Link
              href="/onboarding"
              className="block hover:bg-[var(--color-bg-2)] transition-colors"
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="w-6 text-base shrink-0" aria-hidden="true">
                  📝
                </span>
                <span
                  className="flex-1 text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  Retake lifestyle survey
                </span>
                <span
                  className="text-xs shrink-0"
                  style={{ color: "var(--color-ink-3)" }}
                >
                  Quarterly
                </span>
                <ChevronIcon />
              </div>
            </Link>

            {/* Data sources & devices → #data-sources */}
            <a
              href="#data-sources"
              className="block hover:bg-[var(--color-bg-2)] transition-colors"
              style={rowDivider}
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="w-6 text-base shrink-0" aria-hidden="true">
                  🔗
                </span>
                <span
                  className="flex-1 text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  Data sources &amp; devices
                </span>
                <span
                  className="text-xs shrink-0"
                  style={{ color: "var(--color-ink-3)" }}
                >
                  5 connected
                </span>
                <ChevronIcon />
              </div>
            </a>

            {/* Privacy & consents → #privacy */}
            <a
              href="#privacy"
              className="block hover:bg-[var(--color-bg-2)] transition-colors"
              style={rowDivider}
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="w-6 text-base shrink-0" aria-hidden="true">
                  🔒
                </span>
                <span
                  className="flex-1 text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  Privacy &amp; consents
                </span>
                <ChevronIcon />
              </div>
            </a>

            {/* Notifications → #notifications */}
            <a
              href="#notifications"
              className="block hover:bg-[var(--color-bg-2)] transition-colors"
              style={rowDivider}
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="w-6 text-base shrink-0" aria-hidden="true">
                  🔔
                </span>
                <span
                  className="flex-1 text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  Notifications
                </span>
                <ChevronIcon />
              </div>
            </a>

            {/* Refer a friend — no-op */}
            <button
              type="button"
              className="w-full text-left hover:bg-[var(--color-bg-2)] transition-colors"
              style={rowDivider}
              aria-label="Refer a friend"
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="w-6 text-base shrink-0" aria-hidden="true">
                  🎁
                </span>
                <span
                  className="flex-1 text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  Refer a friend
                </span>
                <ChevronIcon />
              </div>
            </button>

            {/* Sign out — LogoutButton as full-row transparent trigger */}
            <LogoutButton
              className="w-full text-left hover:bg-[var(--color-bg-2)] transition-colors"
              rowStyle={rowDivider}
            />
          </RowList>
        </section>

        {/* ── 5. Data sources ───────────────────────────────────────────── */}
        <section id="data-sources" aria-label="Data sources">
          <SectionHeading>Data Sources</SectionHeading>
          <RowList>
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
                {/* Visual-only toggle — first two enabled for demo */}
                <Switch
                  defaultChecked={idx < 2}
                  aria-label={`Toggle ${src.label}`}
                />
              </div>
            ))}

            {/* Manual tracker rows — read-only, no Switch */}
            {[
              { emoji: "🛌", label: "Sleep log" },
              { emoji: "💧", label: "Water log" },
              { emoji: "🏃", label: "Workout log" },
              { emoji: "📝", label: "Weekly check-in" },
            ].map(({ emoji, label }) => (
              <div
                key={label}
                className="flex items-center justify-between px-4 py-3"
                style={{ borderTop: "1px solid var(--color-border)" }}
              >
                <span
                  className="flex items-center gap-2 text-sm font-medium"
                  style={{ color: "var(--color-ink)" }}
                >
                  <span aria-hidden="true">{emoji}</span>
                  {label}
                </span>
                {/* Manual chip badge */}
                <span
                  className="rounded-full px-2 py-0.5 text-xs font-semibold"
                  style={{
                    backgroundColor: "var(--color-surface-2, var(--color-bg))",
                    border: "1px solid var(--color-border)",
                    color: "var(--color-ink-3)",
                  }}
                >
                  Manual
                </span>
              </div>
            ))}
          </RowList>
        </section>

        {/* ── 6. Consents ───────────────────────────────────────────────── */}
        <section id="consents" aria-label="Consents">
          <SectionHeading>Your Consents</SectionHeading>
          <RowList>
            {CONSENTS.map((item, idx) => (
              <div
                key={item}
                className="flex items-start gap-3 px-4 py-3"
                style={{
                  borderTop:
                    idx > 0 ? "1px solid var(--color-border)" : undefined,
                }}
              >
                {/* Green checkmark */}
                <span
                  className="mt-0.5 text-sm shrink-0"
                  style={{ color: "var(--color-good)" }}
                  aria-hidden="true"
                >
                  ✓
                </span>
                <span
                  className="text-sm"
                  style={{ color: "var(--color-ink-2)" }}
                >
                  {item}
                </span>
              </div>
            ))}
          </RowList>
        </section>

        {/* ── 7. Privacy & GDPR ─────────────────────────────────────────── */}
        <section id="privacy" aria-label="Privacy and data">
          <SectionHeading>Privacy &amp; GDPR</SectionHeading>
          <div
            className="rounded-xl p-4"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            <GdprActions />
          </div>
        </section>
      </div>
    </ScreenFrame>
  );
}
