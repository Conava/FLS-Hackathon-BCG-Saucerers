/**
 * Meal Log page — server component entry point.
 *
 * Renders the MealLogUpload client component and a history section.
 * The history section fetches recent meal logs server-side and passes
 * them as props to avoid a waterfall.
 */

import { Suspense } from "react";
import { MealLogUpload } from "./upload";
import { MealLogHistory } from "./history";
import { LoadingState } from "@/components/design";

/** Server component page — no `"use client"` directive. */
export default function MealLogPage() {
  return (
    <>
      {/* Photo upload + vision analysis (client component) */}
      <MealLogUpload />

      {/* Recent meal history (server-fetched) */}
      <section
        style={{
          padding: "0 16px 32px",
          maxWidth: 480,
          margin: "0 auto",
        }}
      >
        <Suspense fallback={<LoadingState rows={3} card />}>
          <MealLogHistory />
        </Suspense>
      </section>
    </>
  );
}
