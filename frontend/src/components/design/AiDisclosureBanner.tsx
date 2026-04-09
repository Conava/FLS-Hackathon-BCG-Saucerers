import * as React from "react";

export interface AiDisclosureBannerProps {
  /** Optional right-aligned region text, defaults to "EU" */
  region?: string;
}

/**
 * Non-dismissible AI disclosure banner required on all AI-powered screens.
 * Informs the user they are talking to an AI.
 * Uses `role="note"` for a11y.
 */
export function AiDisclosureBanner({
  region = "EU",
}: AiDisclosureBannerProps) {
  return (
    <div
      role="note"
      className="flex items-center"
      style={{
        padding: "10px 14px",
        borderRadius: 14,
        background: "var(--color-violet-lt)",
        color: "var(--color-violet)",
        border: "1px solid rgba(107, 74, 168, 0.18)",
        fontSize: 11.5,
        fontWeight: 600,
      }}
    >
      {/* AI icon */}
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="flex-shrink-0 mr-2"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>

      <span>You&apos;re talking to an AI</span>

      <span
        className="ml-auto"
        style={{ fontSize: 10, opacity: 0.85 }}
      >
        {region}
      </span>
    </div>
  );
}
