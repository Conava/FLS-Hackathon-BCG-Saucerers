/**
 * Records screen — Server Component.
 *
 * Fetches the patient's EHR records list from the backend via BACKEND_URL +
 * patient_id cookie, then hands off to the RecordsContent client component
 * which manages all interactive state (sub-tabs, QA response, etc.).
 *
 * Screen structure (matches mockup/mockup.html #s-records):
 *   1. Page header — h1 "Records" + subtitle
 *   2. AI disclosure banner + Records Q&A card (inside RecordsContent)
 *   3. Plain-language summary card
 *   4. Sub-tabs (All / Labs / Imaging / Visits / Meds / Allergies)
 *   5. Record row-list
 *   6. Biomarker trends section
 *
 * Graceful degradation: cookie missing or 401 => empty records array, no crash.
 *
 * Stack: Next.js 15 App Router, server component, Tailwind v4.
 */

import { cookies } from "next/headers";
import ScreenFrame from "@/components/shell/ScreenFrame";
import type { EHRRecordOut } from "@/lib/api/schemas";
import { RecordsContent } from "./_components/RecordsContent";
import { backendFetch } from "@/lib/backend-fetch";

// -- Types --------------------------------------------------------------------

interface RecordListPayload {
  patient_id: string;
  total: number;
  records?: EHRRecordOut[];
}

// -- Server-side fetch --------------------------------------------------------

/**
 * Fetch the EHR records list for a given patient.
 * Returns null on any error (network failure, 4xx, 5xx).
 */
async function fetchRecords(patientId: string): Promise<RecordListPayload | null> {
  try {
    const res = await backendFetch(`/v1/patients/${patientId}/records`);
    if (!res.ok) return null;
    return (await res.json()) as RecordListPayload;
  } catch {
    return null;
  }
}

// -- Page ---------------------------------------------------------------------

/**
 * Records page — fetches EHR records server-side and passes them to
 * RecordsContent for interactive rendering.
 */
export default async function RecordsPage() {
  const store = await cookies();
  const patientId = store.get("patient_id")?.value;

  const data = patientId ? await fetchRecords(patientId) : null;
  const records = data?.records ?? [];

  return (
    <ScreenFrame>
      <div style={{ padding: "0 16px" }}>
        {/* Page Header */}
        <div style={{ paddingTop: 8, paddingBottom: 16 }}>
          <h1
            className="t-heading-lg text-ink"
            style={{ fontSize: 22, fontWeight: 700 }}
          >
            Records
          </h1>
          <div
            style={{
              fontSize: 13,
              color: "var(--color-ink-3)",
              fontWeight: 500,
              marginTop: 2,
            }}
          >
            Your official clinical data &middot; provider-scoped
          </div>
        </div>

        {/* Interactive records content */}
        <RecordsContent records={records} />

        {/* Bottom breathing room */}
        <div style={{ height: 16 }} />
      </div>
    </ScreenFrame>
  );
}
