import { LoadingState } from "@/components/design";

/**
 * Suspense/streaming loading skeleton for the Insights screen.
 */
export default function InsightsLoading() {
  return (
    <div
      style={{
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <LoadingState rows={1} />
      {/* 2-column signal card grid skeleton */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <LoadingState rows={1} card />
        <LoadingState rows={1} card />
        <LoadingState rows={1} card />
        <LoadingState rows={1} card />
      </div>
      <LoadingState rows={2} card />
    </div>
  );
}
