import { LoadingState } from "@/components/design";

/**
 * Suspense/streaming loading skeleton for the Records screen.
 */
export default function RecordsLoading() {
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
      {/* Q&A box skeleton */}
      <LoadingState rows={1} card />
      {/* Record list skeleton */}
      <LoadingState rows={4} card />
    </div>
  );
}
