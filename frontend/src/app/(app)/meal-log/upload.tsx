"use client";

/**
 * MealLogUpload — client component for the meal photo vision feature.
 *
 * Flow:
 *  1. User picks / captures an image (file input)
 *  2. Preview rendered via object URL
 *  3. "Analyze my meal" posts multipart FormData to the proxy
 *  4. Loading state ("Looking at your plate…") shown during vision processing
 *  5. Result card: meal name, macros, longevity swap tip
 *  6. "Log this meal" navigates back to /today
 *
 * Dev fallback: if the backend fails, a cached demo result is used so the
 * demo never hard-breaks on a cold backend.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { AiDisclosureBanner, MacroRing } from "@/components/design";
import { uploadMealLog } from "@/lib/api/client";
import type { MealLogUploadResponse } from "@/lib/api/schemas";
import { COPY } from "@/lib/copy/copy";

const { mealLog: copy } = COPY;

// ---------------------------------------------------------------------------
// Dev-mode fallback result (demo contingency)
// ---------------------------------------------------------------------------

const DEV_FALLBACK: MealLogUploadResponse = {
  ai_meta: {
    model: "gemini-2.5-flash",
    prompt_name: "meal_vision_demo",
    request_id: "demo-fallback",
    token_in: 0,
    token_out: 0,
    latency_ms: 0,
  },
  meal_log_id: 0,
  photo_uri: "",
  analysis: {
    classification: "Balanced Plate (Demo)",
    macros: {
      protein_g: 30,
      carbs_g: 50,
      fat_g: 15,
      fiber_g: 7,
      polyphenols_mg: 100,
    },
    longevity_swap: "Add a handful of mixed berries on the side",
    swap_rationale: "Berries are rich in anthocyanins linked to reduced oxidative stress",
  },
  disclaimer: "Demo result — backend unavailable.",
};

// ---------------------------------------------------------------------------
// Macro row helper
// ---------------------------------------------------------------------------

interface MacroValue {
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  polyphenols: number;
}

function parseMacros(raw: Record<string, unknown>): MacroValue {
  const n = (k: string) => {
    const v = raw[k];
    return typeof v === "number" ? v : 0;
  };
  return {
    protein: n("protein_g"),
    carbs: n("carbs_g"),
    fat: n("fat_g"),
    fiber: n("fiber_g"),
    polyphenols: n("polyphenols_mg"),
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MealLogUpload() {
  const router = useRouter();

  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [status, setStatus] = React.useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [result, setResult] = React.useState<MealLogUploadResponse | null>(null);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  // Revoke object URL to avoid memory leaks
  React.useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    setSelectedFile(file);
    // Reset previous result
    setResult(null);
    setErrorMsg(null);
    setStatus("idle");
  }

  async function handleAnalyze() {
    if (!selectedFile) return;
    setStatus("loading");
    setErrorMsg(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await uploadMealLog(formData);
      setResult(response);
      setStatus("success");
    } catch (err) {
      // Dev fallback: use demo result so demo never hard-breaks
      if (process.env.NODE_ENV === "development") {
        setResult(DEV_FALLBACK);
        setStatus("success");
        return;
      }
      console.error("[MealLogUpload] upload failed:", err);
      setErrorMsg(copy.error);
      setStatus("error");
    }
  }

  function handleLogMeal() {
    router.push("/today");
  }

  const macros = result ? parseMacros(result.analysis.macros as Record<string, unknown>) : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        padding: "20px 16px",
        maxWidth: 480,
        margin: "0 auto",
      }}
    >
      {/* AI Disclosure banner — non-dismissible, shown at all times */}
      <AiDisclosureBanner />

      {/* Header */}
      <div>
        <h1
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: "var(--color-ink)",
            margin: 0,
          }}
        >
          {copy.title}
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "var(--color-ink-3)",
            marginTop: 4,
            marginBottom: 0,
          }}
        >
          {copy.subtitle}
        </p>
      </div>

      {/* File picker — visually hidden label + styled trigger */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <label
          htmlFor="meal-file-input"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            padding: "12px 20px",
            borderRadius: 14,
            background: "var(--color-bg-2)",
            border: "1.5px dashed var(--color-border)",
            cursor: "pointer",
            fontSize: 15,
            fontWeight: 600,
            color: "var(--color-accent)",
          }}
        >
          {/* Camera icon */}
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
            <circle cx="12" cy="13" r="4" />
          </svg>
          {previewUrl ? copy.cta.chooseFile : copy.cta.takePicture}
        </label>

        {/* Visually hidden input */}
        <input
          id="meal-file-input"
          data-testid="meal-file-input"
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          style={{ position: "absolute", width: 1, height: 1, opacity: 0 }}
          aria-label={copy.cta.takePicture}
        />
      </div>

      {/* Preview */}
      {previewUrl && (
        <div
          style={{
            borderRadius: 16,
            overflow: "hidden",
            aspectRatio: "4/3",
            background: "var(--color-bg-2)",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Selected meal"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      )}

      {/* Analyze button */}
      <button
        type="button"
        disabled={!selectedFile || status === "loading"}
        onClick={handleAnalyze}
        style={{
          padding: "14px 24px",
          borderRadius: 14,
          border: "none",
          background:
            selectedFile && status !== "loading"
              ? "var(--color-accent)"
              : "var(--color-border)",
          color:
            selectedFile && status !== "loading"
              ? "#fff"
              : "var(--color-ink-3)",
          fontSize: 16,
          fontWeight: 700,
          cursor: selectedFile && status !== "loading" ? "pointer" : "not-allowed",
          transition: "background 0.2s",
        }}
        aria-label={copy.cta.analyze}
      >
        {copy.cta.analyze}
      </button>

      {/* Loading state */}
      {status === "loading" && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "14px 16px",
            borderRadius: 14,
            background: "var(--color-bg-2)",
          }}
          aria-live="polite"
          aria-busy="true"
        >
          {/* Spinner */}
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="2.5"
            style={{ animation: "spin 1s linear infinite" }}
            aria-hidden="true"
          >
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </svg>
          <span style={{ fontSize: 15, fontWeight: 600, color: "var(--color-ink-2)" }}>
            {copy.loading}
          </span>
        </div>
      )}

      {/* Error message */}
      {status === "error" && errorMsg && (
        <div
          role="alert"
          style={{
            padding: "12px 16px",
            borderRadius: 14,
            background: "var(--color-warn-lt, #fff3cd)",
            color: "var(--color-warn, #856404)",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* Result card */}
      {status === "success" && result && macros && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
            padding: "16px",
            borderRadius: 16,
            background: "var(--color-bg-2)",
            border: "1px solid var(--color-border)",
          }}
        >
          {/* Meal name */}
          <div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--color-ink-3)",
              }}
            >
              {copy.resultTitle}
            </span>
            <h2
              style={{
                fontSize: 18,
                fontWeight: 700,
                color: "var(--color-ink)",
                margin: "4px 0 0",
              }}
            >
              {result.analysis.classification}
            </h2>
          </div>

          {/* Macro rings row */}
          <div
            style={{
              display: "flex",
              gap: 12,
              overflowX: "auto",
              paddingBottom: 4,
            }}
          >
            <MacroRing
              nutrient="protein"
              value={macros.protein}
              target={60}
              label={copy.macros.protein}
            />
            <MacroRing
              nutrient="fiber"
              value={macros.fiber}
              target={30}
              label={copy.macros.fiber}
            />
            <MacroRing
              nutrient="polyphenols"
              value={macros.polyphenols}
              target={500}
              label={copy.macros.polyphenols}
            />
            <MacroRing
              nutrient="alcohol"
              value={macros.fat}
              target={80}
              label={copy.macros.fat}
            />
          </div>

          {/* Macros text summary */}
          <div
            style={{
              display: "flex",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            {[
              { label: copy.macros.protein, value: `${macros.protein}g` },
              { label: copy.macros.carbs, value: `${macros.carbs}g` },
              { label: copy.macros.fat, value: `${macros.fat}g` },
              { label: copy.macros.fiber, value: `${macros.fiber}g` },
            ].map(({ label, value }) => (
              <div key={label} style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    color: "var(--color-ink)",
                  }}
                >
                  {value}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                    color: "var(--color-ink-3)",
                  }}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>

          {/* Longevity swap card */}
          <div
            style={{
              padding: "12px 14px",
              borderRadius: 12,
              background: "var(--color-good-lt, #e8f5e9)",
              border: "1px solid rgba(56, 142, 60, 0.15)",
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "var(--color-good, #388e3c)",
                display: "block",
                marginBottom: 4,
              }}
            >
              {copy.longevitySwap}
            </span>
            <p
              style={{
                margin: 0,
                fontSize: 14,
                fontWeight: 500,
                color: "var(--color-ink)",
              }}
            >
              {result.analysis.longevity_swap}
            </p>
            {result.analysis.swap_rationale && (
              <p
                style={{
                  margin: "6px 0 0",
                  fontSize: 12,
                  color: "var(--color-ink-3)",
                }}
              >
                {result.analysis.swap_rationale}
              </p>
            )}
          </div>

          {/* Disclaimer */}
          {result.disclaimer && (
            <p
              style={{
                margin: 0,
                fontSize: 11.5,
                color: "var(--color-ink-3)",
                fontStyle: "italic",
              }}
            >
              {result.disclaimer}
            </p>
          )}

          {/* Log this meal CTA */}
          <button
            type="button"
            onClick={handleLogMeal}
            style={{
              padding: "14px 24px",
              borderRadius: 14,
              border: "none",
              background: "var(--color-good, #388e3c)",
              color: "#fff",
              fontSize: 16,
              fontWeight: 700,
              cursor: "pointer",
            }}
            aria-label={copy.cta.logMeal}
          >
            {copy.cta.logMeal}
          </button>
        </div>
      )}
    </div>
  );
}
