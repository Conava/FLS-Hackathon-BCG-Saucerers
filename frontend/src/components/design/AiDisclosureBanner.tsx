import * as React from "react";

export interface AiDisclosureBannerProps {
  /**
   * Optional right-aligned region pill text.
   * Defaults to "EU-only".
   */
  region?: string;
  /**
   * Optional model label appended to the main disclosure text.
   * Defaults to "Gemini 2.5 Flash".
   */
  model?: string;
}

/**
 * Non-dismissible AI disclosure banner required on all AI-powered screens.
 * Shows a circuit icon, disclosure text with model name, and an EU-only pill.
 * Uses `role="note"` for a11y. Not dismissible by design.
 *
 * Matches mockup `.ai-banner`: violet-lt bg, violet text, circuit SVG icon,
 * "You're talking to an AI · Gemini 2.5 Flash", right-aligned "EU-only" span.
 */
export function AiDisclosureBanner({
  region = "EU-only",
  model = "Gemini 2.5 Flash",
}: AiDisclosureBannerProps) {
  return (
    <div
      role="note"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        borderRadius: 14,
        background: "var(--color-violet-lt)",
        color: "var(--color-violet)",
        border: "1px solid rgba(107, 74, 168, 0.18)",
        fontSize: 11.5,
        fontWeight: 600,
      }}
    >
      {/* Circuit / AI chip icon — matches mockup ai-banner SVG path */}
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ flexShrink: 0 }}
        aria-hidden="true"
      >
        <path d="M12 8V4H8M16 4h4v4M4 16v4h4M16 20h4v-4" />
        <rect x="9" y="9" width="6" height="6" rx="1" />
      </svg>

      <span>
        You&apos;re talking to an AI
        {model ? ` · ${model}` : ""}
      </span>

      <span
        style={{ marginLeft: "auto", fontSize: 10, opacity: 0.85 }}
      >
        {region}
      </span>
    </div>
  );
}
