/**
 * Care Screen — Server Component.
 *
 * Fetches appointments, clinical review (stub), and messages in parallel
 * from the backend via BACKEND_URL + patient_id cookie.
 *
 * Renders:
 *   1. Upcoming AppointmentCards
 *   2. Three care pillars: Clinics, Diagnostics, Home Care (CarePillarsClient)
 *   3. ClinicianReviewCard (teal gradient) — stub data from clinical-review
 *   4. Messages thread (MessageBubble list) + MessageComposer
 *
 * BookAppointmentSheet is wired to each PillarCard tap (client-side via
 * CarePillarsClient).
 *
 * Wellness framing: no diagnostic verbs. Every AI screen discloses AI use.
 */

import * as React from "react";
import { cookies } from "next/headers";
import { AppointmentCard } from "@/components/design/AppointmentCard";
import { ClinicianReviewCard } from "@/components/design/ClinicianReviewCard";
import { MessageBubble } from "@/components/design/MessageBubble";
import { SectionHeader } from "@/components/design/SectionHeader";
import { EmptyState } from "@/components/design/EmptyState";
import { COPY } from "@/lib/copy/copy";
import type {
  AppointmentListOut,
  ClinicalReviewResponse,
  MessageListOut,
} from "@/lib/api/schemas";
import { MessageComposer } from "./_components/MessageComposer";
import { CarePillarsClient } from "./_components/CarePillarsClient";
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
        {/* ── Page Header ─────────────────────────────────────── */}
        <div style={{ paddingTop: 8, paddingBottom: 4 }}>
          <h1 className="t-h1 text-ink">{COPY.care.title}</h1>
          <p className="t-body text-ink-3" style={{ marginTop: 4 }}>
            {COPY.care.subtitle}
          </p>
        </div>

        {/* ── Upcoming Appointments ───────────────────────────── */}
        <SectionHeader title="Upcoming Appointments" />
        {appointments.length === 0 ? (
          <EmptyState
            heading="No appointments scheduled"
            subtext="Tap a care pillar below to book."
          />
        ) : (
          <div className="flex flex-col gap-2">
            {appointments.map((appt) => {
              const { day, month } = parseDateBlock(appt.starts_at);
              return (
                <AppointmentCard
                  key={appt.id}
                  day={day}
                  month={month}
                  title={appt.title}
                  clinic={appt.provider}
                  status={appt.location}
                  statusVariant="default"
                />
              );
            })}
          </div>
        )}

        {/* ── Care Pillars ──────────────────────────────────── */}
        <SectionHeader title="Care Pillars" />
        <CarePillarsClient />

        {/* ── Clinician Review ──────────────────────────────── */}
        <SectionHeader title="Clinician Review" />
        {clinicalReviewData ? (
          <ClinicianReviewCard
            name="Dr. Sarah Weber"
            specialty="Longevity Specialist"
            quote={
              clinicalReviewData.notes ||
              "Your latest wellness markers look encouraging. Keep up the positive momentum with your sleep protocol."
            }
            ctaLabel="View full review"
          />
        ) : (
          <ClinicianReviewCard
            name="Dr. Sarah Weber"
            specialty="Longevity Specialist"
            quote="Your wellness journey is progressing well. Continue following your personalized care plan."
            ctaLabel="View full review"
          />
        )}

        {/* ── Messages Thread ───────────────────────────────── */}
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

        {/* ── Message Composer (client component) ────────────── */}
        <MessageComposer />

        {/* Bottom breathing room */}
        <div style={{ height: 16 }} />
      </div>
    </ScreenFrame>
  );
}
