import * as React from "react";

export interface OutlookCurveProps {
  /**
   * Array of projected vitality values — typically 3, 6, or 12 data points.
   * The first point is "now", the last is the furthest projection.
   */
  points: number[];
  /** Label for the current position */
  nowLabel?: string;
  /** Label for the final projected position */
  endLabel?: string;
}

/**
 * SVG sparkline showing a longevity outlook projection.
 * Static data in, no interaction. Uses design token accent color.
 */
export function OutlookCurve({
  points,
  nowLabel = "Now",
  endLabel = "Projection",
}: OutlookCurveProps) {
  if (points.length < 2) return null;

  const W = 320;
  const H = 100;
  const PAD = 10;

  const minVal = Math.min(...points);
  const maxVal = Math.max(...points);
  const range = maxVal - minVal || 1;

  const toX = (i: number) =>
    PAD + (i / (points.length - 1)) * (W - PAD * 2);
  const toY = (v: number) =>
    PAD + (1 - (v - minVal) / range) * (H - PAD * 2);

  const pathD = points
    .map((v, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(v)}`)
    .join(" ");

  const areaD =
    pathD +
    ` L ${toX(points.length - 1)} ${H} L ${toX(0)} ${H} Z`;

  // points.length >= 2 is guaranteed by the early return above
  const dotX = toX(0);
  const dotY = toY(points[0] ?? 0);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      height={H}
      width="100%"
      aria-label="Outlook projection curve"
      role="img"
    >
      <defs>
        <linearGradient id="outlook-fill" x1="0" y1="0" x2="0" y2="1">
          <stop
            offset="0%"
            stopColor="var(--color-accent)"
            stopOpacity="0.25"
          />
          <stop
            offset="100%"
            stopColor="var(--color-accent)"
            stopOpacity="0"
          />
        </linearGradient>
      </defs>

      {/* Gradient area fill */}
      <path d={areaD} fill="url(#outlook-fill)" />

      {/* Stroke line */}
      <path
        d={pathD}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Current dot */}
      <circle cx={dotX} cy={dotY} r="4" fill="var(--color-accent)" />

      {/* Now label */}
      <text
        x={dotX + 6}
        y={dotY - 6}
        fontSize="10"
        fontWeight="700"
        fill="var(--color-accent)"
      >
        {nowLabel}
      </text>

      {/* End label */}
      <text
        x={toX(points.length - 1) - 4}
        y={toY(points[points.length - 1] ?? 0) - 6}
        fontSize="10"
        fontWeight="700"
        fill="var(--color-accent)"
        textAnchor="end"
      >
        {endLabel}
      </text>
    </svg>
  );
}
