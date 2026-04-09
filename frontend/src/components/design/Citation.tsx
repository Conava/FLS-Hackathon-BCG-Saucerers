"use client";

import * as React from "react";

export interface CitationProps {
  /** Reference number or short label */
  label: string | number;
  /** Called when the citation is tapped */
  onClick?: () => void;
}

/**
 * Inline teal badge used in Records Q&A answers to reference source documents.
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
        fontSize: 10.5,
        fontWeight: 600,
        margin: "0 2px",
        cursor: "pointer",
        border: "none",
      }}
      aria-label={`Citation ${label}`}
    >
      [{label}]
    </button>
  );
}
