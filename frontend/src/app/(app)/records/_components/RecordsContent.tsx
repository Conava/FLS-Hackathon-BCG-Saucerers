"use client";

/**
 * RecordsContent — Client Component.
 *
 * Manages interactive state for the Records screen:
 *  - Active sub-tab (All / Labs / Imaging / Visits / Meds / Allergies)
 *  - Q&A response state shared between the QA input card and the
 *    plain-language summary card below it
 *
 * Receives the EHR record list from the server component (page.tsx) as props.
 *
 * Stack: Next.js 15 App Router, client component, Tailwind v4.
 */

import * as React from "react";
import { RecordsQA } from "./RecordsQA";
import type { EHRRecordOut } from "@/lib/api/schemas";

// ── Types ────────────────────────────────────────────────────────────────────

type SubTab = "All" | "Labs" | "Imaging" | "Visits" | "Meds" | "Allergies";

const SUB_TABS: SubTab[] = ["All", "Labs", "Imaging", "Visits", "Meds", "Allergies"];

/** Map record_type prefixes to sub-tab categories */
function recordCategory(recordType: string): SubTab {
  const t = recordType.toLowerCase();
  if (t.includes("lab") || t.includes("panel") || t.includes("blood") || t.includes("cbc"))
    return "Labs";
  if (t.includes("imaging") || t.includes("scan") || t.includes("xray") || t.includes("mri"))
    return "Imaging";
  if (t.includes("visit") || t.includes("consult") || t.includes("check") || t.includes("appointment"))
    return "Visits";
  if (t.includes("med") || t.includes("prescription") || t.includes("drug"))
    return "Meds";
  if (t.includes("allerg"))
    return "Allergies";
  return "All";
}

/** Color-coding for record icon containers, keyed by category */
const ICON_STYLE: Record<SubTab, { bg: string; color: string }> = {
  All:       { bg: "var(--color-accent-lt)",  color: "var(--color-accent)" },
  Labs:      { bg: "var(--color-danger-lt)",  color: "var(--color-danger)" },
  Imaging:   { bg: "var(--color-violet-lt)",  color: "var(--color-violet)" },
  Visits:    { bg: "var(--color-accent-lt)",  color: "var(--color-accent)" },
  Meds:      { bg: "var(--color-good-lt)",    color: "var(--color-good)" },
  Allergies: { bg: "var(--color-warn-lt)",    color: "var(--color-warn)" },
};

/** Emoji for record icon containers, keyed by category */
const ICON_EMOJI: Record<SubTab, string> = {
  All:       "📄",
  Labs:      "🩸",
  Imaging:   "🧬",
  Visits:    "🩺",
  Meds:      "💊",
  Allergies: "⚠️",
};

/** Static biomarker trend rows for demo */
interface BiomarkerRow {
  name: string;
  meta: string;
  value: string;
  status: "good" | "warn" | "danger";
}

const BIOMARKER_ROWS: BiomarkerRow[] = [
  { name: "LDL cholesterol",   meta: "Nov · 3.84 mmol/L · target <3.0", value: "3.84 ▲", status: "warn" },
  { name: "Total cholesterol", meta: "Nov · target <5.0",               value: "7.05 ▲", status: "warn" },
  { name: "Systolic BP",       meta: "Borderline · target <120",        value: "128",     status: "warn" },
  { name: "HbA1c",             meta: "In range",                        value: "5.2% ✓",  status: "good" },
  { name: "Vitamin D",         meta: "In range",                        value: "34 ng/mL ✓", status: "good" },
];

const VALUE_COLORS: Record<BiomarkerRow["status"], string> = {
  good:   "var(--color-good)",
  warn:   "var(--color-warn)",
  danger: "var(--color-danger)",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Format ISO timestamp to short human date, e.g. "Apr 9, 2026". */
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

/** Derive display title from a record. */
function recordTitle(record: EHRRecordOut): string {
  const payloadTitle =
    typeof record.payload["title"] === "string" ? record.payload["title"] : null;
  if (payloadTitle) return payloadTitle;
  return record.record_type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface RecordRowProps {
  record: EHRRecordOut;
}

function RecordRow({ record }: RecordRowProps) {
  const title = recordTitle(record);
  const date = formatDate(record.recorded_at);
  const category = recordCategory(record.record_type);
  const iconStyle = ICON_STYLE[category];
  const emoji = ICON_EMOJI[category];

  return (
    <div
      className="flex items-center gap-3"
      style={{ padding: "12px 14px" }}
    >
      {/* Icon container */}
      <div
        aria-hidden="true"
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: iconStyle.bg,
          color: iconStyle.color,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          fontSize: 18,
        }}
      >
        {emoji}
      </div>

      {/* Text */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 13.5,
            fontWeight: 600,
            color: "var(--color-ink)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontSize: 11.5,
            color: "var(--color-ink-3)",
            marginTop: 2,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {date}
          {record.source ? ` · ${record.source}` : ""}
        </div>
      </div>

      {/* Chevron */}
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
        style={{ color: "var(--color-ink-4)", flexShrink: 0 }}
      >
        <path d="m9 18 6-6-6-6" />
      </svg>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export interface RecordsContentProps {
  /** EHR records fetched server-side; may be empty. */
  records: EHRRecordOut[];
}

/**
 * Interactive records content. Manages sub-tab state and Q&A response state.
 */
export function RecordsContent({ records }: RecordsContentProps) {
  const [activeTab, setActiveTab] = React.useState<SubTab>("All");

  // Filter records by active sub-tab
  const filteredRecords = React.useMemo(() => {
    if (activeTab === "All") return records;
    return records.filter((r) => recordCategory(r.record_type) === activeTab);
  }, [records, activeTab]);

  // Use demo records if backend returned nothing
  const displayRecords = filteredRecords;
  const hasDemoRecords = records.length === 0;

  /** Demo record rows rendered when backend has no data */
  const demoRows: Array<{ id: string; type: SubTab; title: string; meta: string }> = [
    { id: "d1", type: "Labs",    title: "Lipid Panel",      meta: "Nov 2025 · Hamburg clinic · 4 values flagged" },
    { id: "d2", type: "Visits",  title: "Annual check-up",  meta: "Oct 2025 · Dr. Lehmann" },
    { id: "d3", type: "Imaging", title: "CBC + Metabolic",  meta: "Jun 2025 · all in range" },
    { id: "d4", type: "Meds",    title: "Medications",      meta: "None active · ex-smoker since 2019" },
  ];
  const filteredDemoRows = activeTab === "All"
    ? demoRows
    : demoRows.filter((r) => r.type === activeTab);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>

      {/* ── RecordsQA card (banner + input embedded) ──────────────── */}
      <RecordsQA />

      {/* ── Sub-tabs ───────────────────────────────────────────────── */}
      <div
        role="tablist"
        aria-label="Filter records by type"
        style={{
          display: "flex",
          gap: 0,
          marginTop: 14,
          overflowX: "auto",
          scrollbarWidth: "none",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        {SUB_TABS.map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: "0 0 auto",
                padding: "8px 14px",
                fontSize: 12.5,
                fontWeight: isActive ? 700 : 500,
                color: isActive ? "var(--color-accent)" : "var(--color-ink-3)",
                background: "transparent",
                border: "none",
                borderBottom: isActive
                  ? "2px solid var(--color-accent)"
                  : "2px solid transparent",
                cursor: "pointer",
                whiteSpace: "nowrap",
                marginBottom: -1,
              }}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* ── Record list ────────────────────────────────────────────── */}
      <div
        style={{
          borderRadius: 16,
          border: "1px solid var(--color-border)",
          overflow: "hidden",
          marginTop: 10,
        }}
      >
        {hasDemoRecords ? (
          // Demo rows when no backend data
          filteredDemoRows.length === 0 ? (
            <div
              style={{
                padding: "20px 16px",
                textAlign: "center",
                fontSize: 13,
                color: "var(--color-ink-3)",
              }}
            >
              No records in this category.
            </div>
          ) : (
            filteredDemoRows.map((row, index) => {
              const iconStyle = ICON_STYLE[row.type];
              const emoji = ICON_EMOJI[row.type];
              return (
                <React.Fragment key={row.id}>
                  {index > 0 && (
                    <div style={{ height: 1, background: "var(--color-border)", margin: "0 14px" }} />
                  )}
                  <div className="flex items-center gap-3" style={{ padding: "12px 14px" }}>
                    <div
                      aria-hidden="true"
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: iconStyle.bg,
                        color: iconStyle.color,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: 18,
                      }}
                    >
                      {emoji}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--color-ink)" }}>
                        {row.title}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--color-ink-3)", marginTop: 2 }}>
                        {row.meta}
                      </div>
                    </div>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      aria-hidden="true"
                      style={{ color: "var(--color-ink-4)", flexShrink: 0 }}
                    >
                      <path d="m9 18 6-6-6-6" />
                    </svg>
                  </div>
                </React.Fragment>
              );
            })
          )
        ) : displayRecords.length === 0 ? (
          <div
            style={{
              padding: "20px 16px",
              textAlign: "center",
              fontSize: 13,
              color: "var(--color-ink-3)",
            }}
          >
            No records in this category.
          </div>
        ) : (
          displayRecords.map((record, index) => (
            <React.Fragment key={record.id}>
              {index > 0 && (
                <div style={{ height: 1, background: "var(--color-border)", margin: "0 14px" }} />
              )}
              <RecordRow record={record} />
            </React.Fragment>
          ))
        )}
      </div>

      {/* ── Biomarker trends ───────────────────────────────────────── */}
      <div
        className="flex items-center justify-between"
        style={{ marginTop: 20, marginBottom: 10 }}
      >
        <h2
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: "var(--color-ink)",
          }}
        >
          Biomarker trends
        </h2>
        <a
          href="#"
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "var(--color-accent)",
            textDecoration: "none",
          }}
        >
          12m
        </a>
      </div>

      <div
        style={{
          borderRadius: 16,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          overflow: "hidden",
        }}
      >
        {BIOMARKER_ROWS.map((row, index) => (
          <React.Fragment key={row.name}>
            {index > 0 && (
              <div style={{ height: 1, background: "var(--color-border)", margin: "0 14px" }} />
            )}
            <div
              className="flex items-center justify-between"
              style={{ padding: "11px 14px" }}
            >
              <div>
                <div
                  style={{
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: "var(--color-ink)",
                  }}
                >
                  {row.name}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: "var(--color-ink-3)",
                    marginTop: 2,
                  }}
                >
                  {row.meta}
                </div>
              </div>
              <div
                style={{
                  fontSize: 13.5,
                  fontWeight: 700,
                  color: VALUE_COLORS[row.status],
                  flexShrink: 0,
                  marginLeft: 12,
                }}
              >
                {row.value}
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>

      {/* ── Footer disclaimer ──────────────────────────────────────── */}
      <p
        className="t-fine"
        style={{ textAlign: "center", marginTop: 16, marginBottom: 8 }}
      >
        All records provided by your clinic network. No external sources. Not medical advice.
      </p>
    </div>
  );
}
