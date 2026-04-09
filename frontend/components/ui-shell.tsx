import type { ReactNode } from "react";

import type { TabKey } from "@/lib/contracts";
import { cn } from "@/lib/display";

export function SurfaceCard({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[28px] border border-border bg-surface p-5 shadow-[0_10px_30px_rgba(14,23,38,0.06)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
}) {
  return (
    <div className="rounded-2xl bg-panel px-4 py-3">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p
        className={cn(
          "mt-1 font-semibold text-ink",
          compact ? "text-sm leading-5" : "text-base",
        )}
      >
        {value}
      </p>
    </div>
  );
}

export function SeverityBadge({
  severity,
}: {
  severity: "low" | "moderate" | "high";
}) {
  const tone =
    severity === "high"
      ? "bg-danger-soft text-danger"
      : severity === "moderate"
        ? "bg-warn-soft text-warn"
        : "bg-good-soft text-good";

  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 text-xs font-semibold capitalize",
        tone,
      )}
    >
      {severity}
    </span>
  );
}

export function StatusPill({
  children,
  tone,
}: {
  children: ReactNode;
  tone: "accent" | "good" | "neutral";
}) {
  const styles = {
    accent: "bg-accent-soft text-accent",
    good: "bg-good-soft text-good",
    neutral: "bg-panel text-muted",
  } satisfies Record<"accent" | "good" | "neutral", string>;

  return (
    <span className={cn("rounded-full px-3 py-1 text-xs font-semibold", styles[tone])}>
      {children}
    </span>
  );
}

export function StatusBar() {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex h-12 items-center justify-between bg-gradient-to-b from-shell to-transparent px-5 text-xs font-semibold text-ink">
      <span>9:41</span>
      <div className="flex items-center gap-1.5">
        <div className="flex items-end gap-0.5">
          <span className="h-2 w-1 rounded-full bg-current/35" />
          <span className="h-2.5 w-1 rounded-full bg-current/55" />
          <span className="h-3.5 w-1 rounded-full bg-current/75" />
          <span className="h-4.5 w-1 rounded-full bg-current" />
        </div>
        <div className="h-2 w-4 rounded-full border border-current/35" />
        <div className="h-2.5 w-5 rounded-[4px] border border-current/40 p-0.5">
          <div className="h-full w-3 rounded-[2px] bg-current" />
        </div>
      </div>
    </div>
  );
}

export function TabIcon({ tab, active }: { tab: TabKey; active: boolean }) {
  const className = active ? "stroke-[1.9]" : "stroke-[1.8]";

  switch (tab) {
    case "today":
      return (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-5 w-5 fill-none", className)}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3 10.2L12 3l9 7.2V20a1 1 0 0 1-1 1h-5.5v-6.5h-5V21H4a1 1 0 0 1-1-1v-9.8Z" />
        </svg>
      );
    case "coach":
      return (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-5 w-5 fill-none", className)}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-4 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" />
        </svg>
      );
    case "records":
      return (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-5 w-5 fill-none", className)}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
          <path d="M14 3v5h5" />
          <path d="M9 13h6" />
          <path d="M9 17h6" />
        </svg>
      );
    case "insights":
      return (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-5 w-5 fill-none", className)}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 18L10 12l4 4 6-8" />
          <path d="M17 8h3v3" />
        </svg>
      );
    case "care":
      return (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-5 w-5 fill-none", className)}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="4" y="5" width="16" height="15" rx="2" />
          <path d="M8 3v4" />
          <path d="M16 3v4" />
          <path d="M4 10h16" />
        </svg>
      );
    case "me":
      return (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("h-5 w-5 fill-none", className)}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
          <path d="M5 20a7 7 0 0 1 14 0" />
        </svg>
      );
  }
}
