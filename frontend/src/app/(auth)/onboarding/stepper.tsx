"use client";

/**
 * OnboardingStepper — multi-step onboarding questionnaire.
 *
 * Steps:
 *   1. Welcome
 *   2. Connect your data (lifestyle quick form)
 *   3. Set your goals (goal selection)
 *   4. GDPR consent (required toggles before submit)
 *
 * On final step submit: calls submitSurvey({ kind: "onboarding", answers })
 * then navigates to /today.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { StepperProgress } from "@/components/design/StepperProgress";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { submitSurvey } from "@/lib/api/client";
import { COPY, AI_DISCLOSURE } from "@/lib/copy/copy";

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
// Step content
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
  { value: "6_7", label: "6–7h" },
  { value: "7_8", label: "7–8h" },
  { value: "more_8", label: "More than 8h" },
];

const ACTIVITY_OPTIONS = [
  { value: "sedentary", label: "Mostly sedentary" },
  { value: "light", label: "Light (1–2×/week)" },
  { value: "moderate", label: "Moderate (3–4×/week)" },
  { value: "active", label: "Very active (5+×/week)" },
];

const NUTRITION_OPTIONS = [
  { value: "poor", label: "Needs improvement" },
  { value: "fair", label: "Fair — room to grow" },
  { value: "good", label: "Good overall" },
  { value: "excellent", label: "Excellent — mostly whole foods" },
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

function RadioOption({ name, value, label, selected, onChange }: RadioOptionProps) {
  return (
    <label
      className="flex items-center gap-3 rounded-lg border px-4 py-3 cursor-pointer transition-colors"
      style={{
        borderColor: selected ? "var(--color-accent)" : undefined,
        background: selected ? "var(--color-accent-lt, color-mix(in srgb, var(--color-accent) 8%, transparent))" : undefined,
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
      {/* Custom radio indicator */}
      <span
        className="flex-shrink-0 w-5 h-5 rounded-full border-2 inline-flex items-center justify-center"
        style={{
          borderColor: selected ? "var(--color-accent)" : undefined,
        }}
        aria-hidden="true"
      >
        {selected && (
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: "var(--color-accent)" }}
          />
        )}
      </span>
      <span className="text-sm font-medium">{label}</span>
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
    <div className="flex flex-col gap-2">
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

function StepWelcome() {
  const step = COPY.onboarding.steps[0];
  return (
    <div className="flex flex-col items-center text-center gap-4 py-6">
      {/* Logo mark */}
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-black"
        style={{
          background: "var(--color-accent)",
          color: "white",
        }}
        aria-hidden="true"
      >
        h
      </div>
      <div>
        <p
          className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: "var(--color-accent)" }}
        >
          {COPY.app.title}
        </p>
        <h1 className="text-2xl font-extrabold tracking-tight mt-1">
          {step.title}
        </h1>
        <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-ink-3)" }}>
          {step.body}
        </p>
      </div>
      <p className="text-xs" style={{ color: "var(--color-ink-4)" }}>
        {AI_DISCLOSURE}
      </p>
    </div>
  );
}

interface StepGoalProps {
  answers: OnboardingAnswers;
  onChange: (field: keyof OnboardingAnswers, value: string) => void;
}

function StepGoal({ answers, onChange }: StepGoalProps) {
  return (
    <Card>
      <CardHeader>
        <p
          className="text-xs font-bold uppercase tracking-wider"
          style={{ color: "var(--color-accent)" }}
        >
          Your primary goal
        </p>
        <CardTitle className="text-base mt-1">What brings you here?</CardTitle>
        <CardDescription>{COPY.onboarding.steps[2].body}</CardDescription>
      </CardHeader>
      <CardContent>
        <RadioGroup
          name="primaryGoal"
          options={GOAL_OPTIONS}
          value={answers.primaryGoal}
          onChange={(v) => onChange("primaryGoal", v)}
        />
      </CardContent>
    </Card>
  );
}

interface StepLifestyleProps {
  answers: OnboardingAnswers;
  onChange: (field: keyof OnboardingAnswers, value: string) => void;
}

function StepLifestyle({ answers, onChange }: StepLifestyleProps) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">How much do you sleep?</CardTitle>
        </CardHeader>
        <CardContent>
          <RadioGroup
            name="sleepHours"
            options={SLEEP_OPTIONS}
            value={answers.sleepHours}
            onChange={(v) => onChange("sleepHours", v)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">How active are you?</CardTitle>
        </CardHeader>
        <CardContent>
          <RadioGroup
            name="activityLevel"
            options={ACTIVITY_OPTIONS}
            value={answers.activityLevel}
            onChange={(v) => onChange("activityLevel", v)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">How would you rate your nutrition?</CardTitle>
        </CardHeader>
        <CardContent>
          <RadioGroup
            name="nutritionQuality"
            options={NUTRITION_OPTIONS}
            value={answers.nutritionQuality}
            onChange={(v) => onChange("nutritionQuality", v)}
          />
        </CardContent>
      </Card>
    </div>
  );
}

interface StepGDPRProps {
  gdprConsent: boolean;
  onToggle: (checked: boolean) => void;
}

function StepGDPR({ gdprConsent, onToggle }: StepGDPRProps) {
  const step = COPY.onboarding.steps[3];
  return (
    <div className="flex flex-col gap-4">
      <div className="text-center py-4">
        <h2 className="text-xl font-bold tracking-tight">{step.title}</h2>
        <p className="mt-2 text-sm" style={{ color: "var(--color-ink-3)" }}>
          Before we begin, please review and accept our data use terms.
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <Switch
              id="gdpr-consent"
              checked={gdprConsent}
              onCheckedChange={onToggle}
              aria-label="I consent to processing my health data for longevity insights"
            />
            <Label htmlFor="gdpr-consent" className="cursor-pointer">
              <span className="font-semibold text-sm leading-tight block">
                I consent to processing my health data for longevity insights
              </span>
              <span
                className="text-xs mt-1 block leading-relaxed"
                style={{ color: "var(--color-ink-3)" }}
              >
                Art. 9(2)(h) GDPR · EU-hosted (Frankfurt) · Revocable anytime in
                Me → Privacy
              </span>
            </Label>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-center" style={{ color: "var(--color-ink-4)" }}>
        {step.body}
      </p>
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

  return (
    <main className="flex flex-col min-h-screen px-4 pb-8 max-w-lg mx-auto w-full">
      {/* Progress bar */}
      <div className="pt-6 pb-3">
        <StepperProgress total={TOTAL_STEPS} current={step} />
        <p
          className="text-xs text-center mt-2"
          style={{ color: "var(--color-ink-3)" }}
        >
          Step {step} of {TOTAL_STEPS}
        </p>
      </div>

      {/* Step content */}
      <div className="flex-1">
        {step === 1 && <StepWelcome />}
        {step === 2 && (
          <>
            <div className="mb-4">
              <h2 className="text-xl font-bold tracking-tight">
                {COPY.onboarding.steps[1].title}
              </h2>
              <p className="mt-1 text-sm" style={{ color: "var(--color-ink-3)" }}>
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
          <>
            <div className="mb-4">
              <h2 className="text-xl font-bold tracking-tight">
                {COPY.onboarding.steps[2].title}
              </h2>
              <p className="mt-1 text-sm" style={{ color: "var(--color-ink-3)" }}>
                {COPY.onboarding.steps[2].body}
              </p>
            </div>
            <StepGoal
              answers={answers}
              onChange={(field, value) => setField(field, value)}
            />
          </>
        )}
        {step === 4 && (
          <StepGDPR
            gdprConsent={answers.gdprConsent}
            onToggle={(checked) => setField("gdprConsent", checked)}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="flex flex-col gap-3 mt-6">
        {isLastStep ? (
          <Button
            onClick={handleFinish}
            disabled={!answers.gdprConsent || submitting}
            size="lg"
            className="w-full"
          >
            {submitting ? "Saving…" : COPY.onboarding.cta.finish}
          </Button>
        ) : (
          <Button onClick={handleNext} size="lg" className="w-full">
            {COPY.onboarding.cta.next}
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

      {/* Disclaimer */}
      <p
        className="mt-6 max-w-sm text-center text-xs mx-auto"
        style={{ color: "var(--color-ink-4)" }}
      >
        General wellness guidance · Not medical advice · GDPR · EU-only
      </p>
    </main>
  );
}
