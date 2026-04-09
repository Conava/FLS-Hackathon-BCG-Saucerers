import * as React from "react";
import { cn } from "@/lib/utils";

export type ChipVariant =
  | "default"
  | "good"
  | "warn"
  | "danger"
  | "violet"
  | "muted";

const VARIANT_STYLES: Record<ChipVariant, string> = {
  default: "bg-accent-lt text-accent",
  good: "bg-good-lt text-good",
  warn: "bg-warn-lt text-warn",
  danger: "bg-danger-lt text-danger",
  violet: "bg-violet-lt text-violet",
  muted: "bg-bg-2 text-ink-3",
};

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Color variant */
  variant?: ChipVariant;
  /** Show a small colored dot prefix */
  dot?: boolean;
}

/**
 * Inline status badge / tag with 6 semantic color variants.
 * Optionally shows a 6×6 dot prefix in the current text color.
 */
export function Chip({
  variant = "default",
  dot = false,
  className,
  children,
  ...props
}: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5",
        VARIANT_STYLES[variant],
        className
      )}
      style={{ padding: "5px 10px", borderRadius: 999, fontSize: 11, fontWeight: 600 }}
      {...props}
    >
      {dot && (
        <span
          className="rounded-full bg-current"
          style={{ width: 6, height: 6, display: "inline-block", flexShrink: 0 }}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

export interface SuggestedChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Label text */
  label: string;
}

/**
 * Teal-bordered suggested action chip used in the Coach screen.
 * Renders as a button for interactivity.
 */
export function SuggestedChip({ label, className, ...props }: SuggestedChipProps) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center t-support text-ink-2",
        "bg-surface border border-border rounded-full",
        "hover:border-accent hover:text-accent transition-colors",
        className
      )}
      style={{ padding: "8px 12px", borderRadius: 999, fontSize: 12, fontWeight: 600 }}
      {...props}
    >
      {label}
    </button>
  );
}
