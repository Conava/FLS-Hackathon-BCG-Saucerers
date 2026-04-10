import { LoadingState } from "@/components/design";

/**
 * Suspense/streaming loading skeleton for the Care screen.
 */
export default function CareLoading() {
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
      <LoadingState rows={3} card />
      <LoadingState rows={2} card />
    </div>
  );
}
