"use client";

import Link from "next/link";
import { EmptyState } from "@/components/design/EmptyState";
import { COPY } from "@/lib/copy/copy";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Root error boundary — catches unhandled errors from any route segment.
 * Renders a branded error state without exposing raw stack traces.
 * Must be a Client Component (Next.js requirement for error boundaries).
 */
export default function GlobalError({ reset }: ErrorProps) {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100dvh",
        padding: "32px 16px",
        backgroundColor: "var(--color-bg)",
      }}
    >
      <EmptyState
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
        heading={COPY.errors.generic}
        subtext={COPY.errors.network}
        action={
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
            <button
              type="button"
              onClick={reset}
              style={{
                padding: "10px 24px",
                borderRadius: 999,
                background: "var(--color-accent)",
                color: "#ffffff",
                fontSize: 14,
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
              }}
            >
              Try again
            </button>
            <Link
              href="/today"
              style={{
                padding: "10px 24px",
                borderRadius: 999,
                background: "var(--color-bg-2)",
                color: "var(--color-ink-2)",
                fontSize: 14,
                fontWeight: 600,
                textDecoration: "none",
                display: "inline-block",
              }}
            >
              Back to Today
            </Link>
          </div>
        }
      />
    </main>
  );
}
