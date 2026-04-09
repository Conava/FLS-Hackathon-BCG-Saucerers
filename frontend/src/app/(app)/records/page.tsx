/**
 * Records screen — Server Component.
 *
 * Fetches the patient's EHR records list from the backend via BACKEND_URL +
 * patient_id cookie, then renders:
 *   1. Page header
 *   2. RecordsQA client component (AI plain-language Q&A)
 *   3. Record cards list (title, type, date, provider)
 *
 * Graceful degradation: cookie missing or 401 → empty state, no crash.
 *
 * Stack: Next.js 15 App Router, server component, Tailwind v4.
 */

import { cookies } from "next/headers";
import ScreenFrame from "@/components/shell/ScreenFrame";
import { EmptyState } from "@/components/design/EmptyState";
import { COPY } from "@/lib/copy/copy";
import type { EHRRecordOut } from "@/lib/api/schemas";
import { RecordsQA } from "./_components/RecordsQA";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

interface RecordListPayload {
  patient_id: string;
  total: number;
  records?: EHRRecordOut[];
}

// ── Server-side fetch ────────────────────────────────────────────────────────

/**
 * Fetch the EHR records list for a given patient.
 * Returns null on any error (network failure, 4xx, 5xx).
 */
async function fetchRecords(patientId: string): Promise<RecordListPayload | null> {
  try {
    const res = await fetch(
      `${BACKEND_URL}/v1/patients/${patientId}/records`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as RecordListPayload;
  } catch {
    return null;
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Format a stored_at ISO timestamp to a short human date, e.g. "Apr 9, 2026". */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return iso;
  }
}

/**
 * Derive a display title from a record.
 * The payload may contain a `title` field; otherwise fall back to
 * a humanised version of record_type.
 */
function recordTitle(record: EHRRecordOut): string {
  const payloadTitle =
    typeof record.payload["title"] === "string" ? record.payload["title"] : null;
  if (payloadTitle) return payloadTitle;
  return record.record_type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Page ─────────────────────────────────────────────────────────────────────

/**
 * Records page — fetches EHR records server-side and renders the Q&A widget
 * followed by a list of record cards.
 */
export default async function RecordsPage() {
  // Read patient_id from httpOnly cookie
  const store = await cookies();
  const patientId = store.get("patient_id")?.value;

  // Fetch records only when we have a patient ID; otherwise graceful empty state
  const data = patientId ? await fetchRecords(patientId) : null;
  const records = data?.records ?? [];

  return (
    <ScreenFrame>
      <div style={{ padding: "0 16px" }}>
        {/* ── Page Header ─────────────────────────────────────── */}
        <div style={{ paddingTop: 8, paddingBottom: 16 }}>
          <h1
            className="t-heading-lg text-ink"
            style={{ fontSize: 22, fontWeight: 700 }}
          >
            {COPY.records.title}
          </h1>
        </div>

        {/* ── AI Plain-language Q&A ────────────────────────────── */}
        <RecordsQA />

        {/* ── Records List ────────────────────────────────────── */}
        <div style={{ marginTop: 24 }}>
          <h2
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--color-ink-4)",
              marginBottom: 12,
            }}
          >
            {COPY.records.sections.labResults}
          </h2>

          {records.length === 0 ? (
            <EmptyState
              icon={<span style={{ fontSize: 22 }}>&#128196;</span>}
              heading={COPY.records.noRecords}
              subtext={COPY.empty.records}
            />
          ) : (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              {records.map((record) => (
                <RecordCard key={record.id} record={record} />
              ))}
            </div>
          )}
        </div>

        {/* Bottom breathing room */}
        <div style={{ height: 16 }} />
      </div>
    </ScreenFrame>
  );
}

// ── Sub-component ─────────────────────────────────────────────────────────────

/**
 * Single EHR record card — title, type badge, date, provider.
 */
function RecordCard({ record }: { record: EHRRecordOut }) {
  const title = recordTitle(record);
  const date = formatDate(record.recorded_at);

  return (
    <div
      style={{
        borderRadius: 16,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <span
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "var(--color-ink)",
            flex: 1,
          }}
        >
          {title}
        </span>

        {/* Record type badge */}
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            borderRadius: 6,
            padding: "2px 8px",
            background: "var(--color-accent-lt)",
            color: "var(--color-accent)",
            textTransform: "capitalize",
            whiteSpace: "nowrap",
          }}
        >
          {record.record_type.replace(/_/g, " ")}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginTop: 2,
        }}
      >
        {/* Date */}
        <span
          style={{ fontSize: 12, color: "var(--color-ink-3)" }}
        >
          {date}
        </span>

        {/* Provider */}
        {record.source && (
          <>
            <span
              aria-hidden="true"
              style={{ fontSize: 10, color: "var(--color-ink-4)" }}
            >
              &bull;
            </span>
            <span
              style={{ fontSize: 12, color: "var(--color-ink-3)" }}
            >
              {record.source}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
