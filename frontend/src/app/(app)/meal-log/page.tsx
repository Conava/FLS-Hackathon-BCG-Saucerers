/**
 * Meal Log page — server component entry point.
 *
 * Renders the MealLogUpload client component which handles the full
 * Meal vision screen layout matching mockup/mockup.html #s-meal.
 */

import { MealLogUpload } from "./upload";

/** Server component page — no `"use client"` directive. */
export default function MealLogPage() {
  return <MealLogUpload />;
}
