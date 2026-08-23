/**
 * Strict NFL Current-line hygiene.
 *
 * Current on Edge must look like a posted book line. Invalid → null (honest —).
 * Never round / invent a nearby half-point (e.g. −3.58 must not become −3.5).
 */

export type NflMarketLineKind = "spread" | "total" | "ml";

export const SPREAD_ABS_MIN = 0.5;
export const SPREAD_ABS_MAX = 20.5;
export const TOTAL_MIN = 30;
export const TOTAL_MAX = 65;
export const ML_AMERICAN_ABS_MIN = 100;
export const ML_AMERICAN_ABS_MAX = 100_000;
export const ML_DECIMAL_MIN = 1.01;
export const ML_DECIMAL_MAX = 50;

const HALF_POINT_EPS = 1e-6;

export function toFiniteNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function isNflHalfPoint(value: number, eps = HALF_POINT_EPS): boolean {
  const doubled = value * 2;
  return Math.abs(doubled - Math.round(doubled)) < eps;
}

export function canonicalizeHalfPoint(value: number): number {
  return Math.round(value * 2) / 2;
}

export function sanitizeNflSpread(
  value: unknown,
): { value: number; reason: null } | { value: null; reason: string } {
  if (value == null || value === "") return { value: null, reason: "null" };
  const num = toFiniteNumber(value);
  if (num == null) return { value: null, reason: "non_finite" };
  if (Math.abs(num) < 1e-12) return { value: null, reason: "zero" };
  const abs = Math.abs(num);
  if (!isNflHalfPoint(num)) {
    if (abs > 0 && abs < 1)
      return { value: null, reason: "looks_like_probability" };
    if (abs >= ML_AMERICAN_ABS_MIN)
      return { value: null, reason: "looks_like_ml" };
    if (abs >= TOTAL_MIN) return { value: null, reason: "looks_like_total" };
    if (abs > SPREAD_ABS_MAX) return { value: null, reason: "out_of_range" };
    return { value: null, reason: "not_half_point" };
  }
  if (abs >= ML_AMERICAN_ABS_MIN)
    return { value: null, reason: "looks_like_ml" };
  if (abs >= TOTAL_MIN) return { value: null, reason: "looks_like_total" };
  if (abs < SPREAD_ABS_MIN || abs > SPREAD_ABS_MAX) {
    return { value: null, reason: "out_of_range" };
  }
  return { value: canonicalizeHalfPoint(num), reason: null };
}

export function sanitizeNflTotal(
  value: unknown,
): { value: number; reason: null } | { value: null; reason: string } {
  if (value == null || value === "") return { value: null, reason: "null" };
  const num = toFiniteNumber(value);
  if (num == null) return { value: null, reason: "non_finite" };
  if (Math.abs(num) < 1e-12) return { value: null, reason: "zero" };
  if (num > 0 && num < 1)
    return { value: null, reason: "looks_like_probability" };
  if (num < TOTAL_MIN) {
    return {
      value: null,
      reason:
        Math.abs(num) <= SPREAD_ABS_MAX ? "looks_like_spread" : "out_of_range",
    };
  }
  if (num > TOTAL_MAX) return { value: null, reason: "out_of_range" };
  if (!isNflHalfPoint(num)) return { value: null, reason: "not_half_point" };
  return { value: canonicalizeHalfPoint(num), reason: null };
}

export function sanitizeNflMl(
  value: unknown,
): { value: number; reason: null } | { value: null; reason: string } {
  if (value == null || value === "") return { value: null, reason: "null" };
  const num = toFiniteNumber(value);
  if (num == null) return { value: null, reason: "non_finite" };
  if (Math.abs(num) < 1e-12) return { value: null, reason: "zero" };
  if (Math.abs(num) > 0 && Math.abs(num) < 1) {
    return { value: null, reason: "looks_like_probability" };
  }
  if (Math.abs(num - Math.round(num)) < HALF_POINT_EPS) {
    const american = Math.round(num);
    if (
      Math.abs(american) >= ML_AMERICAN_ABS_MIN &&
      Math.abs(american) <= ML_AMERICAN_ABS_MAX
    ) {
      return { value: american, reason: null };
    }
    return { value: null, reason: "out_of_range" };
  }
  if (isNflHalfPoint(num) && Math.abs(num) <= SPREAD_ABS_MAX) {
    return { value: null, reason: "looks_like_spread" };
  }
  const frac = Math.abs(num - Math.trunc(num));
  const tenth = frac * 10;
  if (Math.abs(tenth - Math.round(tenth)) < HALF_POINT_EPS) {
    const digit = Math.round(tenth) % 10;
    if (digit === 2 || digit === 4 || digit === 6 || digit === 8) {
      return { value: null, reason: "looks_like_spread" };
    }
  }
  if (num >= ML_DECIMAL_MIN && num <= ML_DECIMAL_MAX) {
    return { value: Math.round(num * 1000) / 1000, reason: null };
  }
  return { value: null, reason: "not_american_or_decimal_ml" };
}

export function sanitizeNflLine(
  value: unknown,
  kind: NflMarketLineKind,
): number | null {
  if (kind === "spread") return sanitizeNflSpread(value).value;
  if (kind === "total") return sanitizeNflTotal(value).value;
  return sanitizeNflMl(value).value;
}

/** True when a painted Current label (away spread "+3.5" or total "44.5") is book-shaped. */
export function isPlausibleNflCurrentDisplay(
  label: string | null | undefined,
  kind: "spread" | "total",
): boolean {
  if (label == null) return false;
  const raw = String(label).trim();
  if (!raw || raw === "—") return false;
  const n = Number.parseFloat(raw.replace(/[^+\-\d.]/g, ""));
  if (!Number.isFinite(n)) return false;
  if (kind === "total") return sanitizeNflTotal(n).value != null;
  // Board Current for spreads is the away label; validator is home-side agnostic
  // except sign, so ±n both work as long as |n| is a posted spread.
  return (
    sanitizeNflSpread(n).value != null || sanitizeNflSpread(-n).value != null
  );
}
