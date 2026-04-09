/**
 * Care Screen — Server Component.
 *
 * Fetches appointments, clinical review, and messages in parallel from the
 * backend via backendFetch + patient_id cookie.
 *
 * Section order (matches mockup):
 *   1. Header — "Care" + subtitle
 *   2. ClinicianReviewCard — teal gradient, Dr. Lehmann ApoB flag
 *   3. CareSubTabsClient — Clinics / Diagnostics / Home care / Messages / Referrals
 *   4. Upcoming appointments (#care-upcoming)
 *   5. Book a service grid — 2-col (#care-book)
 *   6. Recommended diagnostics card (#care-diagnostics)
 *   7. Messages thread + MessageComposer (#care-messages)
 *
 * Wellness framing: no diagnostic verbs. Every AI screen discloses AI use.
 * GDPR: all queries filtered by patient_id at SQL level.
 */

import * as React from "react";
import { cookies } from "next/headers";
import { AppointmentCard } from "@/components/design/AppointmentCard";
import { ClinicianReviewCard } from "@/components/design/ClinicianReviewCard";
import { MessageBubble } from "@/components/design/MessageBubble";
import { SectionHeader } from "@/components/design/SectionHeader";
import { EmptyState } from "@/components/design/EmptyState";
import type {
  AppointmentListOut,
  ClinicalReviewResponse,
  MessageListOut,
} from "@/lib/api/schemas";
import { MessageComposer } from "./_components/MessageComposer";
import { CareSubTabsClient } from "./_components/CareSubTabsClient";
import { CareServicesGrid } from "./_components/CareServicesGrid";
import ScreenFrame from "@/components/shell/ScreenFrame";
import { backendFetch } from "@/lib/backend-fetch";

// ── Server-side fetch helpers ─────────────────────────────────────────────────

/**
 * Fetch a backend endpoint server-side.
 * Returns null on any error (graceful degradation for demo).
 * Uses backendFetch to inject the X-API-Key header.
 */
async function fetchFromBackend<T>(
  patientId: string,
  path: string,
): Promise<T | null> {
  try {
    const res = await backendFetch(`/v1/patients/${patientId}/${path}`, {
      headers: { "Content-Type": "application/json" },
      next: { revalidate: 30 },
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Format a UTC ISO date string into day number + 3-letter month abbreviation. */
function parseDateBlock(iso: string): { day: number; month: string } {
  const d = new Date(iso);
  const day = d.getUTCDate();
  const month = d
    .toLocaleString("en-US", { month: "short", timeZone: "UTC" })
    .toUpperCase();
  return { day, month };
}

/** Format ISO timestamp into a human-readable short time string. */
function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function CarePage() {
  // Read patient_id from httpOnly cookie
  const store = await cookies();
  const patientId = store.get("patient_id")?.value ?? "PT0199";

  // Fetch in parallel — graceful null on failure
  const [appointmentsData, clinicalReviewData, messagesData] =
    await Promise.all([
      fetchFromBackend<AppointmentListOut>(patientId, "appointments/"),
      fetchFromBackend<ClinicalReviewResponse>(
        patientId,
        "clinical-review?stub=true",
      ),
      fetchFromBackend<MessageListOut>(patientId, "messages"),
    ]);

  const appointments = appointmentsData?.appointments ?? [];
  const messages = messagesData?.messages ?? [];

  return (
    <ScreenFrame>
      <div style={{ padding: "0 16px" }}>
        {/* ── 1. Page Header ──────────────────────────────────── */}
        <div style={{ paddingTop: 8, paddingBottom: 4 }}>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "-0.01em",
              color: "var(--color-ink)",
            }}
          >
            Care
          </h1>
          <p
            style={{
              fontSize: 13,
              color: "var(--color-ink-3)",
              fontWeight: 500,
              marginTop: 4,
            }}
          >
            Your clinic network · clinics, diagnostics, home care
          </p>
        </div>

        {/* ── 2. Clinician Review Card ────────────────────────── */}
        <div style={{ marginTop: 10 }}>
          <ClinicianReviewCard
            initials="DL"
            name="Dr. Lehmann reviewed your ApoB flag"
            specialty="Cardiology · Hamburg Altstadt · 2h ago"
            quote={
              clinicalReviewData?.notes ??
              "I\u2019ve looked at the recent panel. Let\u2019s book an advanced lipid + CIMT for next week. Nothing urgent \u2014 but worth closing the loop given your family history."
            }
            ctaLabel="Confirm follow-up \u00b7 Mon 14 Apr \u00b7 10:30"
          />
        </div>

        {/* ── 3. Sub-tabs ─────────────────────────────────────── */}
        <CareSubTabsClient />

        {/* ── 4. Upcoming appointments ────────────────────────── */}
        <section id="care-upcoming" aria-label="Upcoming appointments">
          <SectionHeader
            title="Upcoming"
            action={
              <a
                href="#care-upcoming"
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--color-accent)",
                  textDecoration: "none",
                }}
                aria-label="Add appointment"
              >
                Add
              </a>
            }
          />
          {appointments.length === 0 ? (
            <>
              {/* Fallback mock appointments matching the mockup */}
              <AppointmentCard
                day={14}
                month="APR"
                title="Cardiology · Dr. Lehmann"
                clinic="10:30 · Hamburg Altstadt · insurance-billed"
                status="In-network"
                statusVariant="good"
              />
              <AppointmentCard
                day={22}
                month="APR"
                title="Dietitian · Lea Brandt"
                clinic="16:00 · video · 45 min"
                status="€0 covered"
                statusVariant="default"
              />
            </>
          ) : (
            appointments.map((appt) => {
              const { day, month } = parseDateBlock(appt.starts_at);
              return (
                <AppointmentCard
                  key={appt.id}
                  day={day}
                  month={month}
                  title={appt.title}
                  clinic={appt.provider}
                  status={appt.location}
                  statusVariant="good"
                />
              );
            })
          )}
        </section>

        {/* ── 5. Book a service grid ──────────────────────────── */}
        <section id="care-book" aria-label="Book a service">
          <SectionHeader title="Book a service" />
          <CareServicesGrid />
        </section>

        {/* ── 6. Recommended diagnostics card ─────────────────── */}
        <section id="care-diagnostics" aria-label="Recommended diagnostics">
          <SectionHeader title="Recommended diagnostics" />
          <div
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 14,
              padding: 16,
            }}
          >
            {/* Top row: title + price */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <p
                  style={{
                    fontSize: 13.5,
                    fontWeight: 700,
                    color: "var(--color-ink)",
                  }}
                >
                  Advanced Lipid + ApoB panel
                </p>
                <p
                  style={{
                    fontSize: 11,
                    color: "var(--color-ink-3)",
                    marginTop: 3,
                  }}
                >
                  Fasting · 30 min · covered by AOK
                </p>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <p
                  style={{
                    fontSize: 16,
                    fontWeight: 800,
                    color: "var(--color-ink)",
                  }}
                >
                  €89
                </p>
                <p
                  style={{
                    fontSize: 10,
                    color: "var(--color-ink-3)",
                    marginTop: 1,
                  }}
                >
                  after insurance
                </p>
              </div>
            </div>

            {/* CTA */}
            <button
              type="button"
              style={{
                marginTop: 12,
                width: "100%",
                padding: "11px 16px",
                background: "var(--color-accent)",
                color: "#fff",
                borderRadius: 12,
                border: "none",
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
              }}
              aria-label="Checkout — Advanced Lipid + ApoB panel"
            >
              Checkout
            </button>
          </div>
        </section>

        {/* ── 7. Messages ─────────────────────────────────────── */}
        <section id="care-messages" aria-label="Messages">
          <SectionHeader title="Messages" />
          <div
            className="flex flex-col gap-3"
            style={{ padding: "12px 0", minHeight: 60 }}
            aria-label="Message thread"
          >
            {messages.length === 0 ? (
              <EmptyState
                heading="No messages yet"
                subtext="Send a message to your care team below."
              />
            ) : (
              messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  sender={msg.direction === "inbound" ? "Care Team" : "You"}
                  content={msg.content}
                  timestamp={formatTime(msg.sent_at)}
                  isOwn={msg.direction === "outbound"}
                />
              ))
            )}
          </div>

          {/* Message Composer */}
          <MessageComposer />
        </section>

        {/* Footer disclaimer */}
        <p
          style={{
            fontSize: 10,
            color: "var(--color-ink-3)",
            textAlign: "center",
            padding: "14px 20px 2px",
          }}
        >
          Real clinicians. In-network. Insurance-billed where applicable.
        </p>

        {/* Bottom breathing room */}
        <div style={{ height: 16 }} />
      </div>
    </ScreenFrame>
  );
}
