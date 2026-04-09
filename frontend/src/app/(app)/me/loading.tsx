import { LoadingState } from "@/components/design";

/**
 * Suspense/streaming loading skeleton for the Me screen.
 */
export default function MeLoading() {
  return (
    <div
      style={{
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      {/* Profile avatar + name */}
      <LoadingState rows={1} card />
      {/* Data sources list */}
      <LoadingState rows={5} card />
      {/* Consents */}
      <LoadingState rows={3} card />
    </div>
  );
}
