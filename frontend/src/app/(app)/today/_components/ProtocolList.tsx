"use client";

import * as React from "react";
import { ProtocolCard } from "@/components/design";
import { EmptyState } from "@/components/design";
import { completeProtocolAction } from "@/lib/api/client";
import type { ProtocolActionOut } from "@/lib/api/schemas";

export interface ProtocolListProps {
  /** Initial list of protocol actions from server-side fetch. */
  actions: ProtocolActionOut[];
}

/**
 * Client component — owns optimistic toggle state for protocol actions.
 * Calls `completeProtocolAction` on click and updates UI immediately
 * before the response returns.
 */
export function ProtocolList({ actions }: ProtocolListProps) {
  // Track optimistic completed state keyed by action id
  const [optimisticDone, setOptimisticDone] = React.useState<
    Record<number, boolean>
  >(() => {
    const initial: Record<number, boolean> = {};
    for (const a of actions) {
      initial[a.id] = a.completed_today ?? false;
    }
    return initial;
  });

  if (actions.length === 0) {
    return (
      <EmptyState
        heading="No protocol yet"
        subtext="Your personalized protocol will appear here once generated."
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
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </svg>
        }
      />
    );
  }

  function handleToggle(action: ProtocolActionOut) {
    // Only complete actions — no "un-complete" in the current API
    if (optimisticDone[action.id]) return;

    // Optimistic update
    setOptimisticDone((prev) => ({ ...prev, [action.id]: true }));

    // Persist to backend (fire-and-forget with rollback on error)
    completeProtocolAction(action.id).catch(() => {
      setOptimisticDone((prev) => ({ ...prev, [action.id]: false }));
    });
  }

  return (
    <ul className="flex flex-col gap-2" style={{ padding: 0, margin: 0 }}>
      {actions.map((action) => (
        <ProtocolCard
          key={action.id}
          action={action.title}
          rationale={action.rationale ?? undefined}
          category={action.category}
          done={optimisticDone[action.id] ?? false}
          onToggle={() => handleToggle(action)}
        />
      ))}
    </ul>
  );
}
