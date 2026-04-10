import { LoadingState } from "@/components/design";

/**
 * Suspense/streaming loading skeleton for the Today screen.
 * Shown while the parallel server fetches are in flight.
 */
export default function TodayLoading() {
  return (
    <div
      style={{
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      {/* Header skeleton */}
      <LoadingState rows={1} />

      {/* Vitality ring skeleton */}
      <div className="flex justify-center">
        <div
          style={{
            width: 168,
            height: 168,
            borderRadius: "50%",
            background: "var(--color-bg-2)",
            animation: "skeleton-shimmer 1.4s linear infinite",
            backgroundSize: "200% 100%",
          }}
          aria-hidden="true"
        />
      </div>

      {/* Outlook curve skeleton */}
      <LoadingState rows={1} card />

      {/* Protocol list skeleton */}
      <LoadingState rows={4} card />

      {/* Macro rings skeleton */}
      <LoadingState rows={1} />
    </div>
  );
}
