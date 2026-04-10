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
  /**
   * Index into `points` that represents "now". Past points (index < nowIndex)
   * are rendered with a dimmer stroke; future points render with the accent
   * colour. Defaults to 0 (all-future curve, original behaviour).
   */
  nowIndex?: number;
}

/**
 * SVG sparkline showing a longevity outlook projection.
 * Static data in, no interaction. Uses design token accent color.
 */
export function OutlookCurve({
  points,
  nowLabel = "Now",
  endLabel = "Projection",
  nowIndex = 0,
}: OutlookCurveProps) {
  if (points.length < 2) return null;
  const nowIdx = Math.max(0, Math.min(points.length - 1, nowIndex));

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

  // Build a smooth cubic bezier path through the points
  const pathD = points
    .map((v, i) => {
      const x = toX(i);
      const y = toY(v);
      if (i === 0) return `M ${x} ${y}`;
      // Control points: use horizontal tension for natural-looking curve
      const prevX = toX(i - 1);
      const prevY = toY(points[i - 1] ?? v);
      const cpX = (prevX + x) / 2;
      return `C ${cpX} ${prevY} ${cpX} ${y} ${x} ${y}`;
    })
    .join(" ");

  const areaD =
    pathD +
    ` L ${toX(points.length - 1)} ${H} L ${toX(0)} ${H} Z`;

  // points.length >= 2 is guaranteed by the early return above
  const dotX = toX(nowIdx);
  const dotY = toY(points[nowIdx] ?? 0);

  // Build a separate path for just the past segment (index 0..nowIdx) so we
  // can render it with a dimmer stroke to distinguish history from projection.
  const pastPath =
    nowIdx > 0
      ? points
          .slice(0, nowIdx + 1)
          .map((v, i) => {
            const x = toX(i);
            const y = toY(v);
            if (i === 0) return `M ${x} ${y}`;
            const prevX = toX(i - 1);
            const prevY = toY(points[i - 1] ?? v);
            const cpX = (prevX + x) / 2;
            return `C ${cpX} ${prevY} ${cpX} ${y} ${x} ${y}`;
          })
          .join(" ")
      : "";

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

      {/* Stroke line — full curve in accent colour */}
      <path
        d={pathD}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Overlay the past segment with a dimmer stroke so history reads
          clearly as "what already happened" vs the projection. */}
      {pastPath && (
        <path
          d={pastPath}
          fill="none"
          stroke="var(--color-ink-2)"
          strokeOpacity="0.5"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

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
