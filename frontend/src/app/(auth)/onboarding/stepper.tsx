"use client";

/**
 * OnboardingStepper — multi-step onboarding questionnaire.
 *
 * Steps:
 *   1. Welcome — logo mark, tagline, hero title, subtitle
 *   2. Lifestyle — sleep, activity, nutrition quick form
 *   3. Goals — primary goal selection
 *   4. GDPR consent — required checkbox before submit
 *
 * On final step submit: calls submitSurvey({ kind: "onboarding", answers })
 * then navigates to /today.
 *
 * Design matches mockup/mockup.html onboarding screen exactly.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { submitSurvey } from "@/lib/api/client";
import { COPY } from "@/lib/copy/copy";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OnboardingAnswers {
  primaryGoal: string;
  sleepHours: string;
  activityLevel: string;
  nutritionQuality: string;
  gdprConsent: boolean;
}

// ---------------------------------------------------------------------------
// Step content constants
// ---------------------------------------------------------------------------

const TOTAL_STEPS = 4;

const GOAL_OPTIONS = [
  { value: "cardiovascular", label: "Understand my cardiovascular risk" },
  { value: "energy", label: "Feel more energy day-to-day" },
  { value: "family", label: "Be healthy for my family long-term" },
  { value: "performance", label: "Optimize performance & recovery" },
];

const SLEEP_OPTIONS = [
  { value: "less_6", label: "Less than 6h" },
  { value: "6_7", label: "6\u20137h" },
  { value: "7_8", label: "7\u20138h" },
  { value: "more_8", label: "More than 8h" },
];

const ACTIVITY_OPTIONS = [
  { value: "sedentary", label: "Mostly sedentary" },
  { value: "light", label: "Light (1\u20132\u00d7/week)" },
  { value: "moderate", label: "Moderate (3\u20134\u00d7/week)" },
  { value: "active", label: "Very active (5+\u00d7/week)" },
];

const NUTRITION_OPTIONS = [
  { value: "poor", label: "Needs improvement" },
  { value: "fair", label: "Fair \u2014 room to grow" },
  { value: "good", label: "Good overall" },
  { value: "excellent", label: "Excellent \u2014 mostly whole foods" },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface RadioOptionProps {
  name: string;
  value: string;
  label: string;
  selected: boolean;
  onChange: (value: string) => void;
}

/**
 * Row-item radio option styled per mockup:
 * 22x22 circular radio, selected = inner filled dot + accent-lt bg + accent border.
 */
function RadioOption({ name, value, label, selected, onChange }: RadioOptionProps) {
  return (
    <label
      className="flex items-center gap-3 cursor-pointer"
      style={{
        padding: "12px 14px",
        borderRadius: "var(--radius-md)",
        border: selected
          ? "1.5px solid var(--color-accent)"
          : "1px solid var(--color-border)",
        background: selected ? "var(--color-accent-lt)" : "transparent",
      }}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={selected}
        onChange={() => onChange(value)}
        className="sr-only"
      />
      {/* 22x22 circular radio indicator */}
      <span
        className="flex-shrink-0 inline-flex items-center justify-center"
        style={{
          width: 22,
          height: 22,
          borderRadius: "999px",
          border: selected
            ? "2px solid var(--color-accent)"
            : "2px solid var(--color-border-2)",
        }}
        aria-hidden="true"
      >
        {selected && (
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "999px",
              background: "var(--color-accent)",
              display: "block",
            }}
          />
        )}
      </span>
      <span className="flex-1 font-medium" style={{ fontSize: 13.5 }}>
        {label}
      </span>
    </label>
  );
}

interface RadioGroupProps {
  name: string;
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
}

function RadioGroup({ name, options, value, onChange }: RadioGroupProps) {
  return (
    <div className="flex flex-col" style={{ gap: 8 }}>
      {options.map((opt) => (
        <RadioOption
          key={opt.value}
          name={name}
          value={opt.value}
          label={opt.label}
          selected={value === opt.value}
          onChange={onChange}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step screens
// ---------------------------------------------------------------------------

/**
 * Step 1 - Welcome screen.
 * Logo mark (56x56 gradient square with white "h"), "WELCOME TO HELF" tagline,
 * hero title "Your longevity, in one place.", and subtitle paragraph.
 */
function StepWelcome() {
  return (
    <div
      className="flex flex-col items-center text-center"
      style={{ padding: "24px 10px 16px" }}
    >
      {/* Logo mark: 56x56, gradient, border-radius var(--radius-md), "h" 24px/800 */}
      <div
        className="flex items-center justify-center"
        style={{
          width: 56,
          height: 56,
          borderRadius: "var(--radius-md)",
          background:
            "linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-2) 100%)",
          color: "#fff",
          fontSize: 24,
          fontWeight: 800,
          marginBottom: 14,
          letterSpacing: "-0.03em",
          flexShrink: 0,
        }}
        aria-hidden="true"
      >
        h
      </div>

      {/* Tagline: 12px/accent/uppercase/0.1em/700 */}
      <div
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: "var(--color-accent)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: 6,
        }}
      >
        Welcome to Helf
      </div>

      {/* Hero title: 26px/800/-0.02em */}
      <h1
        style={{
          fontSize: 26,
          fontWeight: 800,
          letterSpacing: "-0.02em",
          marginBottom: 8,
          lineHeight: 1.2,
        }}
      >
        Your longevity, in one place.
      </h1>

      {/* Subtitle: 13.5px/ink-3/1.55 */}
      <p
        style={{
          fontSize: 13.5,
          color: "var(--color-ink-3)",
          lineHeight: 1.55,
          maxWidth: 300,
        }}
      >
        The only longevity platform where your doctor actually sees the data.
        Part of your clinic network.
      </p>
    </div>
  );
}

interface StepLifestyleProps {
  answers: OnboardingAnswers;
  onChange: (field: keyof OnboardingAnswers, value: string) => void;
}

/** Reusable card wrapper for lifestyle sub-sections. */
function LifestyleCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="flex flex-col"
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "0 1px 3px rgba(14,23,38,.06)",
        padding: 18,
      }}
    >
      <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>{title}</div>
      {children}
    </div>
  );
}

/**
 * Step 2 - Lifestyle quick form: sleep, activity, nutrition.
 */
function StepLifestyle({ answers, onChange }: StepLifestyleProps) {
  return (
    <div className="flex flex-col" style={{ gap: 16 }}>
      <LifestyleCard title="How much do you sleep?">
        <RadioGroup
          name="sleepHours"
          options={SLEEP_OPTIONS}
          value={answers.sleepHours}
          onChange={(v) => onChange("sleepHours", v)}
        />
      </LifestyleCard>

      <LifestyleCard title="How active are you?">
        <RadioGroup
          name="activityLevel"
          options={ACTIVITY_OPTIONS}
          value={answers.activityLevel}
          onChange={(v) => onChange("activityLevel", v)}
        />
      </LifestyleCard>

      <LifestyleCard title="How would you rate your nutrition?">
        <RadioGroup
          name="nutritionQuality"
          options={NUTRITION_OPTIONS}
          value={answers.nutritionQuality}
          onChange={(v) => onChange("nutritionQuality", v)}
        />
      </LifestyleCard>
    </div>
  );
}

interface StepGoalProps {
  answers: OnboardingAnswers;
  onChange: (field: keyof OnboardingAnswers, value: string) => void;
}

/**
 * Step 3 - Primary goal selection.
 * Label "YOUR PRIMARY GOAL" (11px/accent/uppercase/0.08em),
 * Question "What brings you here?" (15px/700), 4 radio options as row-items.
 */
function StepGoal({ answers, onChange }: StepGoalProps) {
  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "0 1px 3px rgba(14,23,38,.06)",
        padding: 18,
      }}
    >
      {/* Section label: 11px/accent/uppercase/0.08em */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "var(--color-accent)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: 4,
        }}
      >
        Your primary goal
      </div>

      {/* Question: 15px/700 */}
      <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>
        What brings you here?
      </div>

      <RadioGroup
        name="primaryGoal"
        options={GOAL_OPTIONS}
        value={answers.primaryGoal}
        onChange={(v) => onChange("primaryGoal", v)}
      />
    </div>
  );
}

interface StepGDPRProps {
  gdprConsent: boolean;
  onToggle: (checked: boolean) => void;
}

/**
 * Step 4 - GDPR consent.
 * Native checkbox (per mockup) + consent text + Art. 9(2)(h) legal note with Learn more link.
 */
function StepGDPR({ gdprConsent, onToggle }: StepGDPRProps) {
  return (
    <div className="flex flex-col" style={{ gap: 16 }}>
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "0 1px 3px rgba(14,23,38,.06)",
          padding: 18,
        }}
      >
        <label
          className="flex cursor-pointer"
          style={{ gap: 12, alignItems: "flex-start" }}
          htmlFor="gdpr-consent"
        >
          <input
            id="gdpr-consent"
            type="checkbox"
            checked={gdprConsent}
            onChange={(e) => onToggle(e.target.checked)}
            style={{
              marginTop: 3,
              accentColor: "var(--color-accent)",
              flexShrink: 0,
            }}
            aria-label="I consent to processing my health data for longevity insights"
          />
          <div>
            <div style={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.4 }}>
              I consent to processing my health data for longevity insights
            </div>
            <div
              style={{
                fontSize: 10.5,
                color: "var(--color-ink-3)",
                marginTop: 4,
                lineHeight: 1.5,
              }}
            >
              Art. 9(2)(h) GDPR &middot; EU-hosted (Frankfurt) &middot; Revocable
              anytime.{" "}
              <a href="#" style={{ color: "var(--color-accent)" }}>
                Learn more.
              </a>
            </div>
          </div>
        </label>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main stepper
// ---------------------------------------------------------------------------

/** Multi-step onboarding questionnaire. Client component. */
export function OnboardingStepper() {
  const router = useRouter();
  const [step, setStep] = React.useState(1);
  const [submitting, setSubmitting] = React.useState(false);
  const [answers, setAnswers] = React.useState<OnboardingAnswers>({
    primaryGoal: "",
    sleepHours: "",
    activityLevel: "",
    nutritionQuality: "",
    gdprConsent: false,
  });

  function setField(field: keyof OnboardingAnswers, value: string | boolean) {
    setAnswers((prev) => ({ ...prev, [field]: value }));
  }

  function handleNext() {
    if (step < TOTAL_STEPS) {
      setStep((s) => s + 1);
    }
  }

  function handleBack() {
    if (step > 1) {
      setStep((s) => s - 1);
    }
  }

  async function handleFinish() {
    if (!answers.gdprConsent) return;
    setSubmitting(true);
    try {
      await submitSurvey({
        kind: "onboarding",
        answers: {
          primaryGoal: answers.primaryGoal,
          sleepHours: answers.sleepHours,
          activityLevel: answers.activityLevel,
          nutritionQuality: answers.nutritionQuality,
          gdprConsent: answers.gdprConsent,
        },
      });
      router.push("/today");
    } finally {
      setSubmitting(false);
    }
  }

  const isLastStep = step === TOTAL_STEPS;

  // Progress bar: step / TOTAL_STEPS * 100 (fills incrementally with each step)
  const progressPct = Math.round((step / TOTAL_STEPS) * 100);

  return (
    <main
      className="flex flex-col min-h-screen w-full mx-auto"
      style={{ maxWidth: 448, padding: "0 20px 28px" }}
    >
      {/* Step 1: welcome hero block shown before progress bar */}
      {step === 1 && <StepWelcome />}

      {/* Progress bar — 4px height, bg-2 track, accent inner span */}
      <div style={{ margin: "10px 0 14px" }}>
        <div
          style={{
            height: 4,
            background: "var(--color-bg-2)",
            borderRadius: 999,
            overflow: "hidden",
          }}
          role="progressbar"
          aria-valuenow={step}
          aria-valuemin={1}
          aria-valuemax={TOTAL_STEPS}
          aria-label={`Step ${step} of ${TOTAL_STEPS}`}
        >
          <span
            style={{
              display: "block",
              height: "100%",
              background: "var(--color-accent)",
              borderRadius: 999,
              width: `${progressPct}%`,
              transition: "width 0.4s ease",
            }}
          />
        </div>
        {/* Caption: 11px/ink-3 */}
        <div
          style={{
            fontSize: 11,
            color: "var(--color-ink-3)",
            textAlign: "center",
            marginTop: 6,
          }}
        >
          Step {step} of {TOTAL_STEPS} &middot; ~3 min
        </div>
      </div>

      {/* Step body */}
      <div className="flex-1">
        {step === 2 && (
          <>
            <div style={{ marginBottom: 16 }}>
              <h2
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  letterSpacing: "-0.01em",
                }}
              >
                {COPY.onboarding.steps[1].title}
              </h2>
              <p
                style={{
                  marginTop: 4,
                  fontSize: 13,
                  color: "var(--color-ink-3)",
                }}
              >
                {COPY.onboarding.steps[1].body}
              </p>
            </div>
            <StepLifestyle
              answers={answers}
              onChange={(field, value) => setField(field, value)}
            />
          </>
        )}
        {step === 3 && (
          <StepGoal
            answers={answers}
            onChange={(field, value) => setField(field, value)}
          />
        )}
        {step === 4 && (
          <StepGDPR
            gdprConsent={answers.gdprConsent}
            onToggle={(checked) => setField("gdprConsent", checked)}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="flex flex-col" style={{ gap: 10, marginTop: 18 }}>
        {isLastStep ? (
          <Button
            onClick={handleFinish}
            disabled={!answers.gdprConsent || submitting}
            size="lg"
            className="w-full"
          >
            {submitting ? "Saving\u2026" : "Finish"}
          </Button>
        ) : (
          <Button onClick={handleNext} size="lg" className="w-full">
            Continue
          </Button>
        )}

        {step > 1 && (
          <Button
            onClick={handleBack}
            variant="ghost"
            size="lg"
            className="w-full"
            disabled={submitting}
          >
            {COPY.onboarding.cta.back}
          </Button>
        )}
      </div>

      {/* Disclaimer: 10.5px/ink-3/center */}
      <p
        className="text-center mx-auto"
        style={{
          marginTop: 16,
          fontSize: 10.5,
          color: "var(--color-ink-3)",
          maxWidth: 320,
          lineHeight: 1.5,
        }}
      >
        Not medical advice. Wellness and lifestyle guidance only.
      </p>
    </main>
  );
}
