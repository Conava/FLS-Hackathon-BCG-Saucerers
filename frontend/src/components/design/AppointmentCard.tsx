import * as React from "react";
import { Chip, type ChipVariant } from "./Chip";

export interface AppointmentCardProps {
  /** Day number, e.g. 14 */
  day: number;
  /** 3-letter month abbreviation, e.g. "MAY" */
  month: string;
  /** Appointment title, e.g. "Blood Panel Review" */
  title: string;
  /** Clinic or subtitle, e.g. "Helf Diagnostic Centre" */
  clinic: string;
  /** Status label shown as a trailing chip */
  status?: string;
  /** Chip color variant for status */
  statusVariant?: ChipVariant;
}

/**
 * Upcoming appointment card with a mini date block, title, clinic, and status chip.
 */
export function AppointmentCard({
  day,
  month,
  title,
  clinic,
  status,
  statusVariant = "default",
}: AppointmentCardProps) {
  return (
    <article
      className="flex gap-3 bg-surface"
      style={{
        padding: 14,
        border: "1px solid var(--color-border)",
        borderRadius: 14,
        marginTop: 8,
      }}
    >
      {/* Date block */}
      <div
        className="flex-shrink-0 flex flex-col items-center justify-center rounded-[10px]"
        style={{
          width: 52,
          height: 56,
          background: "var(--color-accent-lt)",
          color: "var(--color-accent)",
        }}
        aria-label={`${day} ${month}`}
      >
        <span style={{ fontSize: 20, fontWeight: 800, lineHeight: 1 }}>
          {day}
        </span>
        <span
          className="uppercase"
          style={{ fontSize: 10, fontWeight: 700 }}
        >
          {month}
        </span>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="t-body-strong text-ink">{title}</p>
        <p className="t-caption text-ink-3" style={{ marginTop: 2 }}>
          {clinic}
        </p>
      </div>

      {/* Status chip */}
      {status && (
        <div className="flex-shrink-0 self-center">
          <Chip variant={statusVariant}>{status}</Chip>
        </div>
      )}
    </article>
  );
}
