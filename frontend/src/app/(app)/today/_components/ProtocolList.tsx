"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { EmptyState } from "@/components/design";
import { Chip } from "@/components/design";
import { BottomSheet } from "@/components/design";
import {
  completeProtocolAction,
  skipProtocolAction,
  reorderProtocolActions,
} from "@/lib/api/client";
import type { ProtocolActionOut } from "@/lib/api/schemas";
import { cn } from "@/lib/utils";

export interface ProtocolListProps {
  /** Initial list of protocol actions from server-side fetch. */
  actions: ProtocolActionOut[];
}

/** Skip reason options shown in the skip bottom sheet. */
const SKIP_REASONS = ["Too busy", "Didn't feel like it", "Traveling", "Other"] as const;

/**
 * Client component — owns optimistic toggle/skip/reorder state for protocol actions.
 *
 * - Tap the circle to complete an action.
 * - Tap the kebab (…) button to open a skip-reason sheet.
 * - Tap the up/down arrows to reorder actions optimistically.
 *
 * After any mutation, calls `router.refresh()` to re-fetch server data.
 */
export function ProtocolList({ actions }: ProtocolListProps) {
  const router = useRouter();

  // ── Ordered list (optimistic reorder) ──────────────────────────────────────
  const [orderedActions, setOrderedActions] = React.useState<ProtocolActionOut[]>(
    () => [...actions].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
  );

  // ── Optimistic completed state keyed by action id ───────────────────────────
  const [optimisticDone, setOptimisticDone] = React.useState<Record<number, boolean>>(
    () => {
      const initial: Record<number, boolean> = {};
      for (const a of actions) {
        initial[a.id] = a.completed_today ?? false;
      }
      return initial;
    }
  );

  // ── Optimistic skipped state keyed by action id ─────────────────────────────
  const [optimisticSkipped, setOptimisticSkipped] = React.useState<Record<number, boolean>>(
    () => {
      const initial: Record<number, boolean> = {};
      for (const a of actions) {
        initial[a.id] = a.skipped_today ?? false;
      }
      return initial;
    }
  );

  // ── Skip sheet state ────────────────────────────────────────────────────────
  const [skipSheetActionId, setSkipSheetActionId] = React.useState<number | null>(null);

  // ── Empty state ─────────────────────────────────────────────────────────────
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

  // ── Handlers ────────────────────────────────────────────────────────────────

  function handleToggle(action: ProtocolActionOut) {
    // Only complete actions — no "un-complete" in the current API
    if (optimisticDone[action.id] || optimisticSkipped[action.id]) return;

    // Optimistic update
    setOptimisticDone((prev) => ({ ...prev, [action.id]: true }));

    // Persist to backend (fire-and-forget with rollback on error)
    completeProtocolAction(action.id)
      .then(() => router.refresh())
      .catch(() => {
        setOptimisticDone((prev) => ({ ...prev, [action.id]: false }));
      });
  }

  function handleSkip(reason: string) {
    if (skipSheetActionId === null) return;
    const actionId = skipSheetActionId;
    setSkipSheetActionId(null);

    // Optimistic update
    setOptimisticSkipped((prev) => ({ ...prev, [actionId]: true }));

    skipProtocolAction(actionId, reason)
      .then(() => router.refresh())
      .catch(() => {
        setOptimisticSkipped((prev) => ({ ...prev, [actionId]: false }));
      });
  }

  function handleReorder(fromIndex: number, direction: "up" | "down") {
    const toIndex = direction === "up" ? fromIndex - 1 : fromIndex + 1;
    if (toIndex < 0 || toIndex >= orderedActions.length) return;

    // Snapshot the current order BEFORE mutation so the catch closure
    // captures the correct pre-mutation state regardless of re-renders.
    const snapshot = orderedActions;

    const newOrder = [...orderedActions] as ProtocolActionOut[];
    // Swap the two items — use a temp variable so TypeScript is happy with
    // strict array-index typing (destructure assignment targets infer as T|undefined).
    const temp = newOrder[fromIndex] as ProtocolActionOut;
    newOrder[fromIndex] = newOrder[toIndex] as ProtocolActionOut;
    newOrder[toIndex] = temp;
    setOrderedActions(newOrder);

    reorderProtocolActions(newOrder.map((a) => a.id))
      .then(() => router.refresh())
      .catch(() => {
        // Rollback to pre-mutation state
        setOrderedActions(snapshot);
      });
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      <ul className="flex flex-col gap-2" style={{ padding: 0, margin: 0 }}>
        {orderedActions.map((action, index) => {
          const done = optimisticDone[action.id] ?? false;
          const skipped = optimisticSkipped[action.id] ?? false;
          const isFirst = index === 0;
          const isLast = index === orderedActions.length - 1;

          return (
            <li
              key={action.id}
              className="flex items-start gap-3 bg-surface rounded-[14px] list-none"
              style={{
                padding: "12px 14px",
                border: "1px solid var(--color-border)",
              }}
            >
              {/* Check button — dashed border when skipped */}
              <button
                type="button"
                onClick={() => handleToggle(action)}
                aria-label={done ? "Mark as incomplete" : "Mark as complete"}
                aria-pressed={done}
                disabled={skipped}
                className={cn(
                  "flex-shrink-0 flex items-center justify-center rounded-full transition-colors duration-180",
                  done
                    ? "bg-good border-good"
                    : skipped
                    ? "bg-transparent"
                    : "bg-transparent border-border-2"
                )}
                style={{
                  width: 26,
                  height: 26,
                  border: done
                    ? "2px solid var(--color-good)"
                    : skipped
                    ? "2px dashed var(--color-ink-3)"
                    : "2px solid var(--color-border-2)",
                }}
              >
                {done && (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M5 12 10 17 19 7" />
                  </svg>
                )}
              </button>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p
                    className={cn(
                      "t-body-strong",
                      (done || skipped) && "line-through text-ink-3"
                    )}
                    style={{ fontSize: 13.5 }}
                  >
                    {action.title}
                  </p>
                  {skipped && (
                    <Chip variant="muted">Skipped</Chip>
                  )}
                </div>
                {action.rationale && (
                  <p className="t-caption text-ink-3" style={{ marginTop: 2 }}>
                    {action.rationale}
                  </p>
                )}
                {action.category && (
                  <p
                    className="uppercase font-bold text-accent"
                    style={{
                      fontSize: 10,
                      letterSpacing: "0.05em",
                      marginTop: 4,
                    }}
                  >
                    {action.category}
                  </p>
                )}
              </div>

              {/* Right-side controls: kebab + reorder arrows */}
              <div className="flex-shrink-0 flex flex-col items-center gap-0.5">
                {/* Kebab / skip button */}
                {!done && !skipped && (
                  <button
                    type="button"
                    aria-label="Skip options"
                    onClick={() => setSkipSheetActionId(action.id)}
                    className="flex items-center justify-center text-ink-3 hover:text-ink transition-colors rounded"
                    style={{ width: 28, height: 22, fontSize: 16 }}
                  >
                    {/* Three vertical dots */}
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <circle cx="12" cy="5" r="1.5" />
                      <circle cx="12" cy="12" r="1.5" />
                      <circle cx="12" cy="19" r="1.5" />
                    </svg>
                  </button>
                )}

                {/* Reorder: up arrow */}
                <button
                  type="button"
                  aria-label="Move up"
                  disabled={isFirst}
                  onClick={() => handleReorder(index, "up")}
                  className={cn(
                    "flex items-center justify-center rounded transition-colors",
                    isFirst ? "text-border-2 cursor-not-allowed" : "text-ink-3 hover:text-ink"
                  )}
                  style={{ width: 28, height: 20 }}
                >
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M18 15l-6-6-6 6" />
                  </svg>
                </button>

                {/* Reorder: down arrow */}
                <button
                  type="button"
                  aria-label="Move down"
                  disabled={isLast}
                  onClick={() => handleReorder(index, "down")}
                  className={cn(
                    "flex items-center justify-center rounded transition-colors",
                    isLast ? "text-border-2 cursor-not-allowed" : "text-ink-3 hover:text-ink"
                  )}
                  style={{ width: 28, height: 20 }}
                >
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </button>
              </div>
            </li>
          );
        })}
      </ul>

      {/* Skip reason bottom sheet */}
      <BottomSheet
        open={skipSheetActionId !== null}
        onClose={() => setSkipSheetActionId(null)}
        title="Skip this action"
      >
        <div className="flex flex-col gap-3" style={{ marginTop: 16 }}>
          {SKIP_REASONS.map((reason) => (
            <button
              key={reason}
              type="button"
              onClick={() => handleSkip(reason)}
              className="w-full text-left rounded-[12px] bg-bg-2 hover:bg-surface-2 transition-colors t-body text-ink"
              style={{ padding: "14px 16px" }}
            >
              {reason}
            </button>
          ))}
        </div>
      </BottomSheet>
    </>
  );
}
