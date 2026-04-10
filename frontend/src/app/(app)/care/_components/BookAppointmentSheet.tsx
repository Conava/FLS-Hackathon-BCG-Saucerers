"use client";

/**
 * BookAppointmentSheet — BottomSheet opened from a PillarCard tap.
 *
 * Simple form for booking an appointment. On confirm calls
 * POST /api/proxy/appointments/ via the apiClient, then shows a success
 * state and closes.
 *
 * Commerce flows are mocked — no real payment processing.
 */

import * as React from "react";
import { BottomSheet } from "@/components/design/BottomSheet";
import { bookAppointment } from "@/lib/api/client";

export interface BookAppointmentSheetProps {
  /** Whether the sheet is visible */
  open: boolean;
  /** Called when the sheet should close */
  onClose: () => void;
  /** Pillar name shown in the form heading (e.g. "Clinics") */
  pillar: string;
}

/**
 * Bottom-sheet form for booking a care appointment.
 * Submits to the backend and confirms with an inline success state.
 */
export function BookAppointmentSheet({
  open,
  onClose,
  pillar,
}: BookAppointmentSheetProps) {
  const [title, setTitle] = React.useState("");
  const [provider, setProvider] = React.useState("");
  const [date, setDate] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [confirmed, setConfirmed] = React.useState(false);

  const reset = () => {
    setTitle("");
    setProvider("");
    setDate("");
    setConfirmed(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleConfirm = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await bookAppointment({
        title: title || `${pillar} Appointment`,
        provider: provider || "Longevity+ Care",
        location: pillar,
        starts_at: date
          ? new Date(date).toISOString()
          : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        duration_minutes: 30,
      });
      setConfirmed(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <BottomSheet open={open} onClose={handleClose} title="Book Appointment">
      {confirmed ? (
        <div
          className="flex flex-col items-center gap-4"
          style={{ padding: "24px 0" }}
        >
          {/* Check icon */}
          <div
            className="flex items-center justify-center rounded-full"
            style={{
              width: 64,
              height: 64,
              background: "var(--color-accent-lt)",
            }}
            aria-hidden="true"
          >
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <p className="t-body-strong text-ink text-center">
            Appointment booked!
          </p>
          <p className="t-caption text-ink-3 text-center">
            We&apos;ll send a confirmation to your registered email.
          </p>
          <button
            type="button"
            onClick={handleClose}
            className="w-full font-semibold"
            style={{
              marginTop: 8,
              padding: "12px 16px",
              background: "var(--color-accent)",
              color: "#fff",
              borderRadius: 14,
              border: "none",
              fontSize: 15,
              cursor: "pointer",
            }}
          >
            Done
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-4" style={{ marginTop: 16 }}>
          {/* Pillar label */}
          <p className="t-caption text-ink-3">
            Booking for: <span className="text-ink font-semibold">{pillar}</span>
          </p>

          {/* Title */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="appt-title"
              className="t-support text-ink-3"
            >
              Appointment type
            </label>
            <input
              id="appt-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Blood Panel"
              style={{
                padding: "10px 14px",
                borderRadius: 12,
                border: "1px solid var(--color-border)",
                fontSize: 14,
                background: "var(--color-surface)",
                color: "var(--color-ink)",
                outline: "none",
              }}
            />
          </div>

          {/* Provider */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="appt-provider"
              className="t-support text-ink-3"
            >
              Provider
            </label>
            <input
              id="appt-provider"
              type="text"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              placeholder="e.g. Helf Diagnostic Centre"
              style={{
                padding: "10px 14px",
                borderRadius: 12,
                border: "1px solid var(--color-border)",
                fontSize: 14,
                background: "var(--color-surface)",
                color: "var(--color-ink)",
                outline: "none",
              }}
            />
          </div>

          {/* Date */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="appt-date"
              className="t-support text-ink-3"
            >
              Preferred date
            </label>
            <input
              id="appt-date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{
                padding: "10px 14px",
                borderRadius: 12,
                border: "1px solid var(--color-border)",
                fontSize: 14,
                background: "var(--color-surface)",
                color: "var(--color-ink)",
                outline: "none",
              }}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3" style={{ marginTop: 4 }}>
            <button
              type="button"
              onClick={handleClose}
              aria-label="Cancel"
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: 14,
                border: "1px solid var(--color-border)",
                background: "transparent",
                color: "var(--color-ink)",
                fontSize: 15,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleConfirm()}
              disabled={submitting}
              aria-label="Confirm booking"
              style={{
                flex: 2,
                padding: "12px 16px",
                borderRadius: 14,
                border: "none",
                background: submitting
                  ? "var(--color-bg-2)"
                  : "var(--color-accent)",
                color: submitting ? "var(--color-ink-3)" : "#fff",
                fontSize: 15,
                fontWeight: 600,
                cursor: submitting ? "default" : "pointer",
              }}
            >
              {submitting ? "Booking…" : "Confirm"}
            </button>
          </div>
        </div>
      )}
    </BottomSheet>
  );
}
