"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface SegmentedControlOption {
  value: string;
  label: string;
}

export interface SegmentedControlProps {
  /** Available options */
  options: SegmentedControlOption[];
  /** Currently active value */
  value: string;
  /** Called when the user selects a different segment */
  onChange: (value: string) => void;
  /** Additional class names */
  className?: string;
}

/**
 * Pill-style segmented tab switcher (e.g. Records categories, Care pillars).
 */
export function SegmentedControl({
  options,
  value,
  onChange,
  className,
}: SegmentedControlProps) {
  return (
    <div
      className={cn("flex rounded-[14px] p-1", className)}
      style={{ background: "var(--color-bg-2)" }}
      role="tablist"
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "flex-1 text-center transition-all font-semibold",
              active
                ? "bg-surface text-ink shadow-app-sm"
                : "bg-transparent text-ink-3"
            )}
            style={{
              padding: "8px 12px",
              borderRadius: 10,
              fontSize: 12,
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
