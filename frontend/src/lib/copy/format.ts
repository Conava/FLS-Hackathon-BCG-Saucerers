/**
 * Pure formatter functions for display values.
 *
 * All functions are stateless and side-effect-free.
 */

/**
 * Format a wellness score (0–100) as a rounded integer string.
 *
 * @param score - Numeric score, expected 0–100
 * @returns Rounded string, e.g. "82"
 */
export function formatScore(score: number): string {
  return Math.round(score).toString();
}

/**
 * Format a delta value with an explicit + or - sign.
 *
 * @param delta - Positive or negative number
 * @param decimals - Decimal places to show (default 1)
 * @returns e.g. "+2.5" or "-1.0"
 */
export function formatDelta(delta: number, decimals = 1): string {
  const fixed = Math.abs(delta).toFixed(decimals);
  return delta >= 0 ? `+${fixed}` : `-${fixed}`;
}

/**
 * Format a Date or ISO string as a locale date string.
 *
 * @param value - Date object or ISO 8601 string
 * @param locale - BCP 47 locale tag (default "en-GB")
 * @returns e.g. "9 Apr 2026"
 */
export function formatDate(
  value: Date | string,
  locale = "en-GB"
): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return date.toLocaleDateString(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * Format a Date or ISO string as a human-readable relative time string.
 *
 * Uses Intl.RelativeTimeFormat where supported, falling back to formatDate.
 *
 * Thresholds (using floor to avoid early promotion):
 *   < 60 s  → "just now"
 *   < 60 m  → "N minutes ago"
 *   < 24 h  → "N hours ago"
 *   < 30 d  → "N days ago" / "yesterday"
 *   >= 30 d → formatted date string
 *
 * @param value - Date object or ISO 8601 string
 * @param now - Reference point (default: current time) — injectable for testing
 * @returns e.g. "2 hours ago", "yesterday", "3 days ago"
 */
export function formatRelativeTime(
  value: Date | string,
  now: Date = new Date()
): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (diffDays >= 30) {
    return formatDate(date);
  }
  if (diffDays >= 1) {
    return rtf.format(-diffDays, "day");
  }
  if (diffHours >= 1) {
    return rtf.format(-diffHours, "hour");
  }
  if (diffMinutes >= 1) {
    return rtf.format(-diffMinutes, "minute");
  }
  return "just now";
}

/**
 * Format a macro-nutrient value with unit.
 *
 * @param grams - Amount in grams
 * @param unit - Unit label (default "g")
 * @returns e.g. "52 g"
 */
export function formatMacro(grams: number, unit = "g"): string {
  return `${Math.round(grams)} ${unit}`;
}
