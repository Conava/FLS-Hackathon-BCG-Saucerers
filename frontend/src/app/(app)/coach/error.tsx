"use client";

import { EmptyState } from "@/components/design";
import { COPY } from "@/lib/copy/copy";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Error boundary for the Coach screen.
 * Catches runtime errors from page.tsx without exposing raw stack traces.
 */
export default function CoachError({ reset }: ErrorProps) {
  return (
    <div style={{ padding: "16px 20px" }}>
      <EmptyState
        heading={COPY.errors.generic}
        subtext={COPY.errors.network}
        icon={
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        }
        action={
          <button
            type="button"
            onClick={reset}
            className="t-support font-semibold text-accent"
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "8px 16px",
            }}
          >
            Try again
          </button>
        }
      />
    </div>
  );
}
