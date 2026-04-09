import type { EHRRecordOut } from "@/lib/contracts";

export const LONG_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

export const SHORT_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
});

export const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatRecordType(value: string) {
  return value.replaceAll("_", " ");
}

export function describeRecord(record: EHRRecordOut) {
  if (record.record_type === "lab_panel") {
    const ldl = readPayloadNumber(record.payload, "ldl_mmol");
    const total = readPayloadNumber(record.payload, "total_cholesterol_mmol");

    if (ldl != null && total != null) {
      return `Lipid panel - LDL ${ldl.toFixed(2)} mmol/L - total ${total.toFixed(2)} mmol/L`;
    }
  }

  if (record.record_type === "visit") {
    const provider = readPayloadString(record.payload, "provider");
    const notes = readPayloadString(record.payload, "notes");

    if (provider && notes) {
      return `${provider} - ${notes}`;
    }
  }

  return `Record ${record.id}`;
}

export function getInitials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function cn(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

function readPayloadNumber(
  payload: Record<string, unknown>,
  key: string,
): number | null {
  const value = payload[key];

  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function readPayloadString(
  payload: Record<string, unknown>,
  key: string,
) {
  const value = payload[key];
  return typeof value === "string" ? value : null;
}
