import Link from "next/link";
import { EmptyState } from "@/components/design/EmptyState";
import { COPY } from "@/lib/copy/copy";

/**
 * Global not-found (404) page.
 * Renders a branded empty state with a link back to the Today screen.
 */
export default function NotFound() {
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
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        }
        heading={COPY.errors.notFound}
        subtext="The page you're looking for doesn't exist or has moved."
        action={
          <Link
            href="/today"
            style={{
              padding: "10px 24px",
              borderRadius: 999,
              background: "var(--color-accent)",
              color: "#ffffff",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none",
              display: "inline-block",
            }}
          >
            Back to Today
          </Link>
        }
      />
    </main>
  );
}
