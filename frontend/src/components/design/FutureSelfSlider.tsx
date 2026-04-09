"use client";

import * as React from "react";
import { Slider } from "@/components/ui/slider";

export interface FutureSelfSliderProps {
  /** Left-side label, e.g. "Sleep" */
  label: string;
  /** Current value */
  value: number;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Unit string appended to value display, e.g. "hrs" */
  unit?: string;
  /** Called when the user changes the value */
  onChange: (value: number) => void;
}

/**
 * Labeled slider row for the Insights Future Self projection panel.
 * Built on the shadcn Slider primitive with design-token styling.
 */
export function FutureSelfSlider({
  label,
  value,
  min = 0,
  max = 100,
  step = 1,
  unit = "",
  onChange,
}: FutureSelfSliderProps) {
  return (
    <div style={{ marginBottom: 14 }}>
      {/* Label row */}
      <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
        <span className="t-support text-ink">{label}</span>
        <span
          className="t-support font-bold"
          style={{ color: "var(--color-accent)" }}
        >
          {value}
          {unit}
        </span>
      </div>

      {/* Slider */}
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={([v]) => v !== undefined && onChange(v)}
        className="[&_[data-radix-slider-track]]:h-1.5 [&_[data-radix-slider-track]]:bg-bg-2 [&_[data-radix-slider-range]]:bg-accent [&_[data-radix-slider-thumb]]:h-5 [&_[data-radix-slider-thumb]]:w-5 [&_[data-radix-slider-thumb]]:bg-accent [&_[data-radix-slider-thumb]]:border-[3px] [&_[data-radix-slider-thumb]]:border-white"
        aria-label={label}
      />
    </div>
  );
}
