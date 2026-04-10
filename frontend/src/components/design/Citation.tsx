"use client";

import * as React from "react";

export interface CitationProps {
  /** Reference number or short label */
  label: string | number;
  /** Called when the citation is tapped */
  onClick?: () => void;
}

/**
 * Inline teal citation chip used in AI chat bubbles to reference source documents.
 *
 * Matches mockup `.cite`: accent-lt bg, teal text/border, 10.5px / weight 600,
 * 999px radius. Renders inline inside prose text.
 */
export function Citation({ label, onClick }: CitationProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1"
      style={{
        padding: "2px 8px",
        borderRadius: 999,
        background: "var(--color-accent-lt)",
        color: "var(--color-accent)",
        border: "1px solid var(--color-accent-md)",
        fontSize: 10.5,
        fontWeight: 600,
        margin: "0 2px",
        cursor: "pointer",
      }}
      aria-label={`Citation ${label}`}
    >
      [{label}]
    </button>
  );
}
