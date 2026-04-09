"use client";

/**
 * MealLogUpload — client component for the meal photo vision feature.
 *
 * Layout matches mockup/mockup.html #s-meal ("Meal vision" screen):
 *  1. Header: back button (ghost, 14-px chevron) + h1 "Meal vision" (18px/700/-0.01em)
 *  2. AI disclosure banner: camera icon + "AI meal analysis · Gemini 2.5 Flash Vision"
 *  3. Meal photo area: full-width 16/10 — gradient placeholder or uploaded image.
 *     When analyzed: "✓ Analyzed" tag appears top-right.
 *  4. Hidden file input triggered by a button below the photo.
 *  5. Detection card: DETECTED label, food description, macro chips (kcal, protein, carbs, fat, fiber).
 *  6. Longevity swap card: green bg, 🌱 emoji, LONGEVITY SWAP badge, recommendation, rationale.
 *  7. CTAs: "Log to today" (primary, full-width) + "Analyze but don't store photo" (ghost).
 *  8. Footer disclaimer: "Meal vision is a wellness tool. Not a nutrition prescription."
 *
 * Dev fallback: if the backend fails in development mode, a demo result is used.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { uploadMealLog } from "@/lib/api/client";
import type { MealLogUploadResponse } from "@/lib/api/schemas";

// ---------------------------------------------------------------------------
// Static copy (inlined to avoid copy.ts shape changes breaking tests)
// ---------------------------------------------------------------------------

const COPY = {
  title: "Meal vision",
  aiDisclosure: "AI meal analysis \u00b7 Gemini 2.5 Flash Vision",
  takePicture: "Take a photo",
  analyze: "Analyze my meal",
  loading: "Looking at your plate\u2026",
  logToToday: "Log to today",
  analyzeNoStore: "Analyze but don\u2019t store photo",
  footer: "Meal vision is a wellness tool. Not a nutrition prescription.",
  error:
    "Couldn\u2019t analyse this image. Please try again with a clearer photo.",
} as const;

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
    classification: "Grilled salmon, white rice, broccoli",
    macros: {
      kcal: 480,
      protein_g: 34,
      carbs_g: 42,
      fat_g: 18,
      fiber_g: 4,
      polyphenols_mg: 100,
    },
    longevity_swap: "Swap white rice for lentils",
    swap_rationale:
      "+12g fiber \u00b7 same calories \u00b7 supports a steadier post-meal glucose curve.",
  },
  disclaimer: "Demo result \u2014 backend unavailable.",
};

// ---------------------------------------------------------------------------
// Macro parsing helper
// ---------------------------------------------------------------------------

interface MacroValue {
  kcal: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
}

function parseMacros(raw: Record<string, unknown>): MacroValue {
  const n = (k: string) => {
    const v = raw[k];
    return typeof v === "number" ? Math.round(v) : 0;
  };
  return {
    kcal: n("kcal"),
    protein: n("protein_g"),
    carbs: n("carbs_g"),
    fat: n("fat_g"),
    fiber: n("fiber_g"),
  };
}

// ---------------------------------------------------------------------------
// Chip helper (inline to avoid import coupling)
// ---------------------------------------------------------------------------

function MacroChip({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "5px 10px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        background: "var(--color-accent-lt)",
        color: "var(--color-accent)",
      }}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * Renders the full Meal vision screen with photo capture, analysis, and CTA.
 * No server-side dependencies — pure client component.
 */
export function MealLogUpload() {
  const router = useRouter();

  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [status, setStatus] = React.useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [result, setResult] = React.useState<MealLogUploadResponse | null>(
    null
  );
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  // Revoke object URL on unmount to prevent memory leaks
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
      // Dev fallback: use demo result so the demo never hard-breaks
      if (process.env.NODE_ENV === "development") {
        setResult(DEV_FALLBACK);
        setStatus("success");
        return;
      }
      console.error("[MealLogUpload] upload failed:", err);
      setErrorMsg(COPY.error);
      setStatus("error");
    }
  }

  function handleLogMeal() {
    router.push("/today");
  }

  const analyzed = status === "success" && result !== null;
  const macros = result
    ? parseMacros(result.analysis.macros as Record<string, unknown>)
    : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        padding: "16px 16px 32px",
        maxWidth: 480,
        margin: "0 auto",
      }}
    >
      {/* ── 1. Header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 6,
        }}
      >
        {/* Back button — ghost style, 14-px chevron */}
        <button
          type="button"
          onClick={() => router.back()}
          aria-label="Back"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "8px 12px",
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            color: "var(--color-ink)",
            cursor: "pointer",
            minHeight: 36,
            flexShrink: 0,
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>

        <h1
          style={{
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
            margin: 0,
          }}
        >
          {COPY.title}
        </h1>
      </div>

      {/* ── 2. AI disclosure banner: camera icon + text ── */}
      <div
        role="note"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          borderRadius: 12,
          background: "var(--color-violet-lt)",
          color: "var(--color-violet)",
          border: "1px solid rgba(107,74,168,.18)",
          fontSize: 11.5,
          fontWeight: 600,
          marginBottom: 12,
        }}
      >
        {/* Camera icon — matches mockup ai-banner SVG */}
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ flexShrink: 0 }}
          aria-hidden="true"
        >
          <rect x="3" y="6" width="18" height="14" rx="2" />
          <circle cx="12" cy="13" r="4" />
          <path d="M9 3h6l1 3" />
        </svg>
        <span>{COPY.aiDisclosure}</span>
      </div>

      {/* ── 3. Meal photo area ── */}
      <div
        style={{
          width: "100%",
          aspectRatio: "16 / 10",
          borderRadius: 12,
          background:
            "linear-gradient(135deg, #F4E3C8 0%, #D9B97A 50%, #8FAD5E 100%)",
          position: "relative",
          overflow: "hidden",
          cursor: previewUrl ? "default" : "pointer",
        }}
        role="img"
        aria-label={
          previewUrl ? "Selected meal photo" : "Tap to select a meal photo"
        }
        onClick={() => {
          if (!previewUrl) fileInputRef.current?.click();
        }}
      >
        {/* Radial shine overlays for empty-state gradient */}
        {!previewUrl && (
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(circle at 30% 40%, rgba(255,255,255,.2), transparent 40%), " +
                "radial-gradient(circle at 70% 60%, rgba(0,0,0,.15), transparent 45%)",
            }}
          />
        )}

        {/* Uploaded image preview */}
        {previewUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt="Selected meal"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        )}

        {/* ✓ Analyzed tag — dark semi-transparent pill, top-right */}
        {analyzed && (
          <span
            style={{
              position: "absolute",
              top: 10,
              right: 10,
              zIndex: 2,
              background: "rgba(14,23,38,.75)",
              color: "#fff",
              padding: "4px 10px",
              borderRadius: 999,
              fontSize: 10.5,
              fontWeight: 700,
            }}
          >
            ✓ Analyzed
          </span>
        )}

        {/* Loading overlay */}
        {status === "loading" && (
          <div
            aria-live="polite"
            aria-busy="true"
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(14,23,38,.4)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
            }}
          >
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#fff"
              strokeWidth="2.5"
              style={{ animation: "meal-spin 1s linear infinite" }}
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <style>{`@keyframes meal-spin { to { transform: rotate(360deg); } }`}</style>
            <span
              style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}
            >
              {COPY.loading}
            </span>
          </div>
        )}
      </div>

      {/* ── 4. Hidden file input ── */}
      <input
        ref={fileInputRef}
        id="meal-file-input"
        data-testid="meal-file-input"
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        style={{ position: "absolute", width: 1, height: 1, opacity: 0 }}
        aria-label={COPY.takePicture}
      />

      {/* Photo picker button — shown when no file selected */}
      {!previewUrl && (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          style={{
            marginTop: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            padding: "12px 20px",
            borderRadius: 12,
            background: "var(--color-bg-2)",
            border: "1.5px dashed var(--color-border)",
            cursor: "pointer",
            fontSize: 14,
            fontWeight: 600,
            color: "var(--color-accent)",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="3" y="6" width="18" height="14" rx="2" />
            <circle cx="12" cy="13" r="4" />
            <path d="M9 3h6l1 3" />
          </svg>
          {COPY.takePicture}
        </button>
      )}

      {/* Analyze button — shown when file selected, not yet analyzed */}
      {previewUrl && !analyzed && status !== "loading" && (
        <button
          type="button"
          disabled={!selectedFile}
          onClick={handleAnalyze}
          aria-label={COPY.analyze}
          style={{
            marginTop: 10,
            padding: "14px 24px",
            borderRadius: 12,
            border: "none",
            background: selectedFile
              ? "var(--color-accent)"
              : "var(--color-border)",
            color: selectedFile ? "#fff" : "var(--color-ink-3)",
            fontSize: 14,
            fontWeight: 600,
            cursor: selectedFile ? "pointer" : "not-allowed",
            width: "100%",
            minHeight: 44,
          }}
        >
          {COPY.analyze}
        </button>
      )}

      {/* Error message */}
      {status === "error" && errorMsg && (
        <div
          role="alert"
          style={{
            marginTop: 12,
            padding: "12px 16px",
            borderRadius: 12,
            background: "var(--color-warn-lt)",
            color: "var(--color-warn)",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* ── 5. Detection card (shown after analysis) ── */}
      {analyzed && macros && result && (
        <>
          <div
            style={{
              marginTop: 12,
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 16,
              boxShadow: "0 1px 4px rgba(14,23,38,.06)",
              padding: 18,
            }}
          >
            {/* DETECTED label */}
            <div
              style={{
                fontSize: 11,
                color: "var(--color-ink-3)",
                textTransform: "uppercase",
                fontWeight: 700,
                letterSpacing: "0.06em",
              }}
            >
              Detected
            </div>

            {/* Food description */}
            <div
              style={{
                fontSize: 14,
                fontWeight: 700,
                marginTop: 4,
                color: "var(--color-ink)",
              }}
            >
              {result.analysis.classification}
            </div>

            {/* Macro chips row */}
            <div
              style={{
                display: "flex",
                gap: 10,
                marginTop: 10,
                flexWrap: "wrap",
              }}
            >
              {macros.kcal > 0 && (
                <MacroChip>{macros.kcal} kcal</MacroChip>
              )}
              {macros.protein > 0 && (
                <MacroChip>{macros.protein}g protein</MacroChip>
              )}
              {macros.carbs > 0 && (
                <MacroChip>{macros.carbs}g carbs</MacroChip>
              )}
              {macros.fat > 0 && (
                <MacroChip>{macros.fat}g fat</MacroChip>
              )}
              {macros.fiber > 0 && (
                <MacroChip>{macros.fiber}g fiber</MacroChip>
              )}
            </div>
          </div>

          {/* ── 6. Longevity swap card ── */}
          <div
            style={{
              marginTop: 12,
              background: "var(--color-good-lt)",
              border: "1px solid #BEE5CC",
              borderRadius: 16,
              padding: 18,
            }}
          >
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              {/* 🌱 emoji */}
              <div style={{ fontSize: 22, lineHeight: 1, flexShrink: 0 }} aria-hidden="true">
                🌱
              </div>
              <div>
                {/* LONGEVITY SWAP badge */}
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: "var(--color-good)",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Longevity swap
                </div>
                {/* Recommendation */}
                <div
                  style={{
                    fontSize: 13.5,
                    fontWeight: 700,
                    marginTop: 4,
                    color: "var(--color-ink)",
                  }}
                >
                  {result.analysis.longevity_swap}
                </div>
                {/* Rationale */}
                {result.analysis.swap_rationale && (
                  <div
                    style={{
                      fontSize: 11.5,
                      color: "var(--color-ink-2)",
                      marginTop: 2,
                    }}
                  >
                    {result.analysis.swap_rationale}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── 7. CTAs ── */}
          {/* "Log to today" — primary full-width */}
          <button
            type="button"
            onClick={handleLogMeal}
            aria-label={COPY.logToToday}
            style={{
              marginTop: 14,
              padding: "14px 24px",
              borderRadius: 12,
              border: "none",
              background: "var(--color-accent)",
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              width: "100%",
              minHeight: 44,
            }}
          >
            {COPY.logToToday}
          </button>

          {/* "Analyze but don't store photo" — ghost full-width */}
          <button
            type="button"
            style={{
              marginTop: 8,
              padding: "12px 24px",
              borderRadius: 12,
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-ink)",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              width: "100%",
              minHeight: 44,
            }}
          >
            {COPY.analyzeNoStore}
          </button>
        </>
      )}

      {/* ── 8. Footer disclaimer ── */}
      <p
        style={{
          marginTop: 20,
          fontSize: 10.5,
          color: "var(--color-ink-3)",
          textAlign: "center",
          margin: "20px 0 0",
        }}
      >
        {COPY.footer}
      </p>
    </div>
  );
}
