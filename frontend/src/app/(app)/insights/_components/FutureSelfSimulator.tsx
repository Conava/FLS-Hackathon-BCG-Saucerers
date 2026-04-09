"use client";

/**
 * FutureSelfSimulator — client component for the Insights screen.
 *
 * Renders a section header ("Future-self simulator" + "10Y HORIZON" chip),
 * then a card containing:
 *   - Projected age display: two columns "Current path" (warn) | "Improved path" (good)
 *   - Three Radix sliders: Sleep (5-9 h), Activity (0-7 sessions/wk), Alcohol (0-14 units/wk)
 *   - "Apply to my outlook" block CTA
 *
 * On slider change (debounced 400 ms), calls postFutureSelf and updates
 * the "Improved path" projected age. Wellness-framing compliant.
 */

import * as React from "react";
import { FutureSelfSlider } from "@/components/design";
import { postFutureSelf } from "@/lib/api/client";

/** Debounce delay before firing the API call */
const DEBOUNCE_MS = 400;

/** Default slider values matching realistic baselines */
const DEFAULTS = {
  sleep: 7.5,
  activity: 4,
  alcohol: 2,
};

/**
 * Future-self projection panel.
 *
 * Shows "Current path" vs "Improved path" biological age at 70,
 * with three interactive sliders that debounce-trigger a projection call.
 */
export function FutureSelfSimulator() {
  const [sleep, setSleep] = React.useState(DEFAULTS.sleep);
  const [activity, setActivity] = React.useState(DEFAULTS.activity);
  const [alcohol, setAlcohol] = React.useState(DEFAULTS.alcohol);

  /** Projected bio age from the API (null = not yet fetched, show demo) */
  const [projectedAge, setProjectedAge] = React.useState<number | null>(null);
  const [loading, setLoading] = React.useState(false);

  /** Default "current path" demo age — warn/amber */
  const currentPathAge = 71;
  /** Improved path: use API result or demo baseline */
  const improvedAge = projectedAge ?? 64;

  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = React.useRef(true);

  React.useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, []);

  /**
   * Debounced projection call. Cancels any in-flight timer, then waits
   * DEBOUNCE_MS before hitting the API.
   */
  const scheduleProjection = React.useCallback(
    (nextSleep: number, nextActivity: number, nextAlcohol: number) => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);

      timerRef.current = setTimeout(async () => {
        if (!mountedRef.current) return;
        setLoading(true);

        try {
          const result = await postFutureSelf({
            patient_id: "me",
            sliders: {
              sleep_hours: nextSleep,
              activity_minutes: nextActivity * 45, // sessions to approximate minutes
              alcohol_units_per_week: nextAlcohol,
            },
          });
          if (mountedRef.current) setProjectedAge(result.bio_age);
        } catch {
          // Silently keep the demo value — wellness tool, not clinical
        } finally {
          if (mountedRef.current) setLoading(false);
        }
      }, DEBOUNCE_MS);
    },
    [],
  );

  const handleSleepChange = (v: number) => {
    setSleep(v);
    scheduleProjection(v, activity, alcohol);
  };

  const handleActivityChange = (v: number) => {
    setActivity(v);
    scheduleProjection(sleep, v, alcohol);
  };

  const handleAlcoholChange = (v: number) => {
    setAlcohol(v);
    scheduleProjection(sleep, activity, v);
  };

  return (
    <section aria-label="Future-self simulator">
      {/* Section header: h-row style */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          margin: "0 0 10px",
        }}
      >
        <h2
          style={{
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: "0.01em",
            textTransform: "uppercase",
            color: "var(--color-ink)",
          }}
        >
          Future-self simulator
        </h2>
        <span className="chip chip-violet">10Y Horizon</span>
      </div>

      {/* Card */}
      <div className="card">
        {/* Projected age display */}
        <div style={{ textAlign: "center", padding: "6px 0 12px" }}>
          {/* Label: 11px/ink-3/uppercase/0.06em */}
          <p
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-ink-3)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: 8,
            }}
          >
            Projected biological age at 70
          </p>

          {/* Two-column: current | arrow | improved */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "baseline",
              gap: 18,
            }}
          >
            {/* Current path — warn */}
            <div>
              <p
                style={{ fontSize: 11, color: "var(--color-ink-3)", marginBottom: 2 }}
              >
                Current path
              </p>
              <span
                style={{
                  fontSize: 28,
                  fontWeight: 800,
                  color: "var(--color-warn)",
                  fontVariantNumeric: "tabular-nums",
                  lineHeight: 1,
                  display: "block",
                }}
                aria-label={"Current path: " + currentPathAge}
              >
                {currentPathAge}
              </span>
            </div>

            {/* Separator arrow */}
            <span
              style={{ fontSize: 18, color: "var(--color-ink-3)" }}
              aria-hidden="true"
            >
              →
            </span>

            {/* Improved path — good */}
            <div>
              <p
                style={{ fontSize: 11, color: "var(--color-ink-3)", marginBottom: 2 }}
              >
                Improved path
              </p>
              <span
                style={{
                  fontSize: 28,
                  fontWeight: 800,
                  color: loading ? "var(--color-ink-3)" : "var(--color-good)",
                  fontVariantNumeric: "tabular-nums",
                  lineHeight: 1,
                  display: "block",
                }}
                aria-live="polite"
                aria-busy={loading}
                aria-label={"Improved path: " + improvedAge}
              >
                {loading ? "…" : improvedAge}
              </span>
            </div>
          </div>
        </div>

        {/* Sliders: Sleep 5-9h, Activity 0-7 sessions/wk, Alcohol 0-14 units/wk */}
        <FutureSelfSlider
          label="Sleep"
          value={sleep}
          min={5}
          max={9}
          step={0.5}
          unit="h"
          onChange={handleSleepChange}
        />
        <FutureSelfSlider
          label="Activity"
          value={activity}
          min={0}
          max={7}
          step={1}
          unit=" sessions/wk"
          onChange={handleActivityChange}
        />
        <FutureSelfSlider
          label="Alcohol"
          value={alcohol}
          min={0}
          max={14}
          step={1}
          unit=" units/wk"
          onChange={handleAlcoholChange}
        />

        {/* CTA: "Apply to my outlook" — primary block */}
        <button
          type="button"
          style={{
            display: "block",
            width: "100%",
            marginTop: 6,
            padding: "11px 0",
            borderRadius: 10,
            background: "var(--color-accent)",
            color: "#fff",
            fontSize: 13.5,
            fontWeight: 600,
            border: "none",
            cursor: "pointer",
            textAlign: "center",
          }}
        >
          Apply to my outlook
        </button>
      </div>
    </section>
  );
}
