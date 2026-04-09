"use client";

/**
 * FutureSelfSimulator — client component for the Insights screen.
 *
 * Renders three FutureSelfSlider rows (sleep, activity, alcohol).
 * On slider change (debounced 400 ms), calls postFutureSelf and displays
 * the projected biological age at 70.
 *
 * AI disclosure banner is shown above the sliders (GDPR / MDR requirement).
 */

import * as React from "react";
import { AiDisclosureBanner, FutureSelfSlider } from "@/components/design";
import { postFutureSelf } from "@/lib/api/client";
import { COPY } from "@/lib/copy/copy";

/** Local copy strings for this component (wellness framing compliant). */
const STRINGS = {
  sectionTitle: "Future Self Simulator",
  subtitle: "Adjust your lifestyle habits to see your projected biological age at 70",
  sliders: {
    sleep: "Sleep",
    activity: "Activity",
    alcohol: "Alcohol",
  },
  sliderUnits: {
    sleep: " hrs",
    activity: " min",
    alcohol: " units/wk",
  },
  projectedLabel: "Projected biological age at 70",
  loading: "Projecting\u2026",
};

/** Default slider values matching realistic baselines */
const DEFAULTS = {
  sleep: 7,
  activity: 30,
  alcohol: 3,
};

/** Slider range config */
const SLIDER_CONFIG = {
  sleep: { min: 4, max: 12, step: 0.5 },
  activity: { min: 0, max: 120, step: 5 },
  alcohol: { min: 0, max: 21, step: 1 },
};

/** Debounce delay in ms before firing the API call */
const DEBOUNCE_MS = 400;

/**
 * Renders the interactive Future Self projection panel.
 * Calls the backend whenever sliders settle (debounced).
 */
export function FutureSelfSimulator() {
  const [sleep, setSleep] = React.useState(DEFAULTS.sleep);
  const [activity, setActivity] = React.useState(DEFAULTS.activity);
  const [alcohol, setAlcohol] = React.useState(DEFAULTS.alcohol);

  const [projectedAge, setProjectedAge] = React.useState<number | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  /** Stable ref for debounce timer */
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Track whether the component is still mounted (avoids setState after unmount) */
  const mountedRef = React.useRef(true);
  React.useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /**
   * Debounced handler — cancels any pending request, waits DEBOUNCE_MS,
   * then calls postFutureSelf with the current slider values.
   */
  const scheduleProjection = React.useCallback(
    (nextSleep: number, nextActivity: number, nextAlcohol: number) => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }

      timerRef.current = setTimeout(async () => {
        if (!mountedRef.current) return;

        setLoading(true);
        setError(null);

        try {
          const result = await postFutureSelf({
            patient_id: "me",
            sliders: {
              sleep_hours: nextSleep,
              activity_minutes: nextActivity,
              alcohol_units_per_week: nextAlcohol,
            },
          });

          if (mountedRef.current) {
            setProjectedAge(result.bio_age);
          }
        } catch {
          if (mountedRef.current) {
            setError(COPY.errors.generic);
          }
        } finally {
          if (mountedRef.current) {
            setLoading(false);
          }
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
    <section
      aria-label={STRINGS.sectionTitle}
      style={{ display: "flex", flexDirection: "column", gap: 16 }}
    >
      {/* AI disclosure banner — required before any AI-generated output */}
      <AiDisclosureBanner />

      {/* Section header */}
      <div>
        <h2
          className="t-heading-sm text-ink"
          style={{ marginBottom: 2 }}
        >
          {STRINGS.sectionTitle}
        </h2>
        <p className="t-caption text-ink-3">{STRINGS.subtitle}</p>
      </div>

      {/* Sliders */}
      <div
        style={{
          padding: 16,
          borderRadius: 14,
          border: "1px solid var(--color-border)",
          background: "var(--color-surface)",
        }}
      >
        <FutureSelfSlider
          label={STRINGS.sliders.sleep}
          value={sleep}
          min={SLIDER_CONFIG.sleep.min}
          max={SLIDER_CONFIG.sleep.max}
          step={SLIDER_CONFIG.sleep.step}
          unit={STRINGS.sliderUnits.sleep}
          onChange={handleSleepChange}
        />
        <FutureSelfSlider
          label={STRINGS.sliders.activity}
          value={activity}
          min={SLIDER_CONFIG.activity.min}
          max={SLIDER_CONFIG.activity.max}
          step={SLIDER_CONFIG.activity.step}
          unit={STRINGS.sliderUnits.activity}
          onChange={handleActivityChange}
        />
        <FutureSelfSlider
          label={STRINGS.sliders.alcohol}
          value={alcohol}
          min={SLIDER_CONFIG.alcohol.min}
          max={SLIDER_CONFIG.alcohol.max}
          step={SLIDER_CONFIG.alcohol.step}
          unit={STRINGS.sliderUnits.alcohol}
          onChange={handleAlcoholChange}
        />
      </div>

      {/* Projected age result */}
      <div
        style={{
          padding: 16,
          borderRadius: 14,
          border: "1px solid var(--color-border)",
          background: "var(--color-surface)",
          minHeight: 72,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 4,
        }}
      >
        {loading ? (
          <p
            className="t-support text-ink-3"
            aria-live="polite"
            aria-busy="true"
          >
            {STRINGS.loading}
          </p>
        ) : error ? (
          <p
            className="t-support"
            style={{ color: "var(--color-danger)" }}
            aria-live="polite"
          >
            {error}
          </p>
        ) : projectedAge !== null ? (
          <>
            <span
              className="t-stat-lg tabular-nums"
              style={{ color: "var(--color-accent)" }}
              aria-live="polite"
            >
              {projectedAge}
            </span>
            <p className="t-caption text-ink-3">{STRINGS.projectedLabel}</p>
          </>
        ) : (
          <p className="t-caption text-ink-3" aria-live="polite">
            {STRINGS.subtitle}
          </p>
        )}
      </div>
    </section>
  );
}
