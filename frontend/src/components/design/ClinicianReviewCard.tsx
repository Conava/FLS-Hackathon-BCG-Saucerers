import * as React from "react";

export interface ClinicianReviewCardProps {
  /** Clinician full name */
  name: string;
  /** Clinician role / specialty */
  specialty?: string;
  /** Review or message excerpt */
  quote: string;
  /** CTA button label */
  ctaLabel?: string;
  /** Called when CTA is tapped */
  onCta?: () => void;
  /** Initials shown in the avatar when no image is provided */
  initials?: string;
}

/**
 * Teal gradient clinician review / message card for the Care screen.
 * White text, no box-shadow — gradient handles depth.
 */
export function ClinicianReviewCard({
  name,
  specialty,
  quote,
  ctaLabel = "View full review",
  onCta,
  initials,
}: ClinicianReviewCardProps) {
  const derived = initials ?? name.slice(0, 2).toUpperCase();

  return (
    <div
      style={{
        background:
          "linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-2) 100%)",
        color: "#fff",
        padding: 18,
        borderRadius: 20,
      }}
    >
      {/* Top row: avatar + info + message button */}
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div
          className="flex-shrink-0 flex items-center justify-center rounded-full font-bold"
          style={{
            width: 44,
            height: 44,
            background: "rgba(255,255,255,0.2)",
            fontSize: 14,
          }}
          aria-hidden="true"
        >
          {derived}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p style={{ fontSize: 13.5, fontWeight: 600 }}>{name}</p>
          {specialty && (
            <p style={{ fontSize: 11.5, opacity: 0.8, marginTop: 1 }}>
              {specialty}
            </p>
          )}
        </div>

        {/* Ghost message button */}
        <button
          type="button"
          className="flex items-center gap-1"
          style={{
            background: "rgba(255,255,255,0.15)",
            color: "#fff",
            padding: "6px 10px",
            borderRadius: 10,
            fontSize: 11.5,
            fontWeight: 600,
            border: "none",
          }}
          aria-label="Message clinician"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Message
        </button>
      </div>

      {/* Quote */}
      <p
        style={{
          fontSize: 12,
          lineHeight: 1.55,
          opacity: 0.95,
          marginTop: 12,
        }}
      >
        &ldquo;{quote}&rdquo;
      </p>

      {/* CTA */}
      <button
        type="button"
        onClick={onCta}
        className="w-full font-semibold"
        style={{
          marginTop: 12,
          padding: "8px 12px",
          background: "#fff",
          color: "var(--color-accent-2)",
          borderRadius: 10,
          fontSize: 12.5,
          border: "none",
          cursor: "pointer",
        }}
      >
        {ctaLabel}
      </button>
    </div>
  );
}
