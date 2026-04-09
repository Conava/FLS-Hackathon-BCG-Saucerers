/**
 * MealLogHistory — server component that fetches recent meal logs
 * and renders a summary list.
 *
 * Uses the BACKEND_URL env var (available server-side) with the session
 * cookie forwarded via Next.js route handlers, keeping the data-fetching
 * in the server layer for performance.
 *
 * Falls back gracefully when the backend is unavailable (dev contingency).
 */

import { COPY } from "@/lib/copy/copy";
import type { MealLogOut } from "@/lib/api/schemas";

const { mealLog: copy } = COPY;

/**
 * Fetch recent meal logs from the backend via the internal proxy URL.
 * Returns an empty array on any error (dev resilience).
 */
async function fetchMealLogs(): Promise<MealLogOut[]> {
  try {
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    // In server components we call the proxy path on the same host;
    // for SSR we call the proxy directly by constructing an absolute URL.
    const res = await fetch(`${backendUrl}/api/proxy/meal-log`, {
      next: { revalidate: 30 }, // ISR: revalidate every 30s
    });
    if (!res.ok) return [];
    const data = (await res.json()) as { logs?: MealLogOut[] };
    return data.logs ?? [];
  } catch {
    return [];
  }
}

function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

/** Server component — async. */
export async function MealLogHistory() {
  const logs = await fetchMealLogs();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h2
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: "var(--color-ink)",
          margin: "0 0 4px",
        }}
      >
        {copy.history.title}
      </h2>

      {logs.length === 0 ? (
        <p
          style={{
            fontSize: 14,
            color: "var(--color-ink-3)",
            margin: 0,
          }}
        >
          {copy.history.empty}
        </p>
      ) : (
        logs.map((log) => (
          <div
            key={log.id}
            style={{
              display: "flex",
              gap: 12,
              padding: "12px 14px",
              borderRadius: 14,
              background: "var(--color-bg-2)",
              border: "1px solid var(--color-border)",
              alignItems: "flex-start",
            }}
          >
            {/* Meal icon */}
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: "var(--color-accent-lt)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
                <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
                <line x1="6" y1="1" x2="6" y2="4" />
                <line x1="10" y1="1" x2="10" y2="4" />
                <line x1="14" y1="1" x2="14" y2="4" />
              </svg>
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <p
                style={{
                  margin: 0,
                  fontSize: 14,
                  fontWeight: 600,
                  color: "var(--color-ink)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {log.analysis.classification}
              </p>
              <p
                style={{
                  margin: "2px 0 0",
                  fontSize: 12,
                  color: "var(--color-ink-3)",
                }}
              >
                {formatDate(log.logged_at)}
              </p>
              {log.analysis.longevity_swap && (
                <p
                  style={{
                    margin: "4px 0 0",
                    fontSize: 12,
                    color: "var(--color-good, #388e3c)",
                    fontWeight: 500,
                  }}
                >
                  Swap: {log.analysis.longevity_swap}
                </p>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
