/**
 * Player Futures column doctrine (2026-08-11):
 * Every player-future row shows Projected | Current (YTD) | Current odds.
 *
 * Current conventions:
 * - Counting stats (yards / receptions / TDs / team wins): 2026 REG YTD only.
 *   Preseason / no REG games → 0 (never prior-season backfill, never empty).
 * - Award-only rows (MVP / OPOY): Current = "—" — no fake award progress.
 * - Missing odds → "—" (never invent).
 */

import { formatAmericanOdds } from "@/lib/american-odds";

export const CURRENT_YTD_TOOLTIP =
  "Current = 2026 YTD (0 before Week 1)";

export const AWARD_CURRENT_CONVENTION: "emdash" = "emdash";

export type PlayerFutureCurrentKind = "counting" | "award";

export type PlayerFutureOddsSnap = {
  american: number | null;
  book: string | null;
  asOfUtc: string | null;
};

/** Format Projected values with optional units (visible in UI). */
export function formatProjectedValue(
  value: number | null | undefined,
  opts?: { digits?: number; unit?: string; percent?: boolean },
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const digits = opts?.digits ?? 0;
  let body: string;
  if (opts?.percent) {
    body = `${(value * 100).toFixed(digits)}%`;
  } else {
    body = digits > 0 ? value.toFixed(digits) : String(Math.round(value));
  }
  return opts?.unit ? `${body} ${opts.unit}` : body;
}

/**
 * Current (YTD) display.
 * Counting → 0 when null/missing (preseason smoke).
 * Award → always "—" (no YTD award progress).
 */
export function formatCurrentYtd(
  value: number | null | undefined,
  kind: PlayerFutureCurrentKind,
  digits = 0,
): string {
  if (kind === "award") return "—";
  const n = value == null || !Number.isFinite(value) ? 0 : value;
  return digits > 0 ? n.toFixed(digits) : String(Math.round(n));
}

/** Current odds display — never invent. */
export function formatCurrentOdds(
  snap: PlayerFutureOddsSnap | null | undefined,
): string {
  if (!snap || snap.american == null) return "—";
  return formatAmericanOdds(snap.american);
}

export function formatCurrentOddsWithBook(
  snap: PlayerFutureOddsSnap | null | undefined,
): { price: string; book: string | null; asOfUtc: string | null } {
  return {
    price: formatCurrentOdds(snap),
    book: snap?.book ?? null,
    asOfUtc: snap?.asOfUtc ?? null,
  };
}

/** Sum nullable yard/TD fields; treat all-null as missing (→ Current 0 via format). */
export function sumNullable(
  ...values: Array<number | null | undefined>
): number | null {
  if (values.every((v) => v == null)) return null;
  return values.reduce<number>((sum, v) => sum + (v ?? 0), 0);
}
