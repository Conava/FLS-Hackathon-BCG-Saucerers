import * as React from "react";

export interface LoadingStateProps {
  /** Number of skeleton rows to render */
  rows?: number;
  /** Whether to show a wider "card" skeleton shape */
  card?: boolean;
}

/**
 * Skeleton loading placeholder wrapper.
 * Renders shimmer rows while content is being fetched.
 */
export function LoadingState({ rows = 3, card = false }: LoadingStateProps) {
  return (
    <div className="flex flex-col gap-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <SkeletonRow width="100%" height={card ? 80 : 16} />
          {!card && <SkeletonRow width="70%" height={12} />}
        </div>
      ))}
    </div>
  );
}

function SkeletonRow({
  width,
  height,
}: {
  width: string | number;
  height: number;
}) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: 8,
        background:
          "linear-gradient(90deg, var(--color-bg-2) 0%, var(--color-border) 50%, var(--color-bg-2) 100%)",
        backgroundSize: "200% 100%",
        animation: "skeleton-shimmer 1.4s linear infinite",
      }}
      aria-hidden="true"
    >
      <style>{`
        @keyframes skeleton-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          * { animation-duration: 0.01ms !important; }
        }
      `}</style>
    </div>
  );
}
