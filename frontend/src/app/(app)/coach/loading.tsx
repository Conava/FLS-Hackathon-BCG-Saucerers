import { LoadingState } from "@/components/design";

/**
 * Suspense/streaming loading skeleton for the Coach screen.
 */
export default function CoachLoading() {
  return (
    <div
      style={{
        padding: "72px 20px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <LoadingState rows={1} />
      <LoadingState rows={4} card />
    </div>
  );
}
