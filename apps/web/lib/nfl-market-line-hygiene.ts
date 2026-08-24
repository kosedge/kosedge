/**
 * NFL Current-line hygiene — simple book-line gate.
 *
 * Spread valid if: number in [-20, 20] AND (integer or *.0 or *.5).
 * Total valid if: number in [30, 65] AND (integer or *.0 or *.5).
 * Else Current for that market is null (honest —). Never round junk.
 * Never reject because Current equals Open.
 */

export type NflMarketLineKind = "spread" | "total" | "ml";

export const SPREAD_MIN = -20;
export const SPREAD_MAX = 20;
export const TOTAL_MIN = 30;
export const TOTAL_MAX = 65;
export const ML_AMERICAN_ABS_MIN = 100;
export const ML_AMERICAN_ABS_MAX = 100_000;

const HALF_POINT_EPS = 1e-6;
const DASHES = /[\u2212\u2012\u2013\u2014\u2015\uff0d]/g;

export function normalizeNumericText(raw: string): string {
  return raw.trim().replace(DASHES, "-");
}

export function toFiniteNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const text = normalizeNumericText(String(value));
  if (!text || text === "—" || text === "-") return null;
  const n = Number(text);
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
  if (num < SPREAD_MIN || num > SPREAD_MAX)
    return { value: null, reason: "out_of_range" };
  if (!isNflHalfPoint(num)) return { value: null, reason: "not_half_point" };
  return { value: canonicalizeHalfPoint(num), reason: null };
}

export function sanitizeNflTotal(
  value: unknown,
): { value: number; reason: null } | { value: null; reason: string } {
  if (value == null || value === "") return { value: null, reason: "null" };
  const num = toFiniteNumber(value);
  if (num == null) return { value: null, reason: "non_finite" };
  if (num < TOTAL_MIN || num > TOTAL_MAX)
    return { value: null, reason: "out_of_range" };
  if (!isNflHalfPoint(num)) return { value: null, reason: "not_half_point" };
  return { value: canonicalizeHalfPoint(num), reason: null };
}

export function sanitizeNflMl(
  value: unknown,
): { value: number; reason: null } | { value: null; reason: string } {
  if (value == null || value === "") return { value: null, reason: "null" };
  const num = toFiniteNumber(value);
  if (num == null) return { value: null, reason: "non_finite" };
  if (Math.abs(num - Math.round(num)) >= HALF_POINT_EPS) {
    return { value: null, reason: "not_american_ml" };
  }
  const american = Math.round(num);
  if (
    Math.abs(american) < ML_AMERICAN_ABS_MIN ||
    Math.abs(american) > ML_AMERICAN_ABS_MAX
  ) {
    return { value: null, reason: "out_of_range" };
  }
  return { value: american, reason: null };
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
  const n = toFiniteNumber(raw);
  if (n == null) return false;
  if (kind === "total") return sanitizeNflTotal(n).value != null;
  return (
    sanitizeNflSpread(n).value != null || sanitizeNflSpread(-n).value != null
  );
}
