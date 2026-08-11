/**
 * Central Edge Board Tag Policy thresholds (2026-08-11).
 *
 * Doctrine: we bet prices, not teams. Tags are mechanical.
 * Edge / Tag = KEI vs best available market only.
 * Edge magnitude and confidence stay separate — never one mysterious score.
 *
 * Mirrors services/model-service/src/services/nfl_tag_policy.py
 */

export const BREAKEVEN_ATS_MINUS_110 = 0.5238;

export const COVER_PASS_MAX = 0.53;
export const COVER_LEAN_MAX = 0.54;
export const COVER_PLAY_MAX = 0.56;
export const COVER_STRONG_MAX = 0.58;
export const COVER_MODEL_WARNING = 0.6;

export type SidePointThresholds = {
  passMax: number;
  leanMax: number;
  playMin: number;
  strongMin: number;
};

export type TotalPointThresholds = {
  passMax: number;
  leanMax: number;
  playMin: number;
  strongMin: number;
};

/** Weeks 1–2 (tighter) — 2026-08-11 brief. */
export const EARLY_SIDE: SidePointThresholds = {
  passMax: 1.25,
  leanMax: 1.75,
  playMin: 2.25,
  strongMin: 3.25,
};

/** Midseason baseline (after Week 2). */
export const STANDARD_SIDE: SidePointThresholds = {
  passMax: 1.0,
  leanMax: 1.5,
  playMin: 2.0,
  strongMin: 3.0,
};

export const INSEASON_SIDE: SidePointThresholds = STANDARD_SIDE;

export const BASELINE_TOTAL: TotalPointThresholds = {
  passMax: 1.5,
  leanMax: 2.0,
  playMin: 2.5,
  strongMin: 3.5,
};

/** Week 1–2: +0.25 pt on each totals band → 1.75 / 2.25 / 2.75 / 3.75. */
export const WEEK1_TOTAL_BOOST = 0.25;

export const EARLY_TOTAL: TotalPointThresholds = {
  passMax: BASELINE_TOTAL.passMax + WEEK1_TOTAL_BOOST,
  leanMax: BASELINE_TOTAL.leanMax + WEEK1_TOTAL_BOOST,
  playMin: BASELINE_TOTAL.playMin + WEEK1_TOTAL_BOOST,
  strongMin: BASELINE_TOTAL.strongMin + WEEK1_TOTAL_BOOST,
};

export const TOTAL_PASS_MAX = BASELINE_TOTAL.passMax;
export const TOTAL_STRONG_MIN = BASELINE_TOTAL.strongMin;

export const CONFIDENCE_PLAY_MIN = 0.55;
export const CONFIDENCE_BEST_BET_MIN = 0.75;
export const CONFIDENCE_TIER_BASE = 0.72;

export const SPREAD_KEY_NUMBERS = [3, 7, 10, 14] as const;
export const TOTAL_KEY_NUMBERS = [37, 41, 44, 47, 51] as const;

export type WeekRegime = "early" | "standard" | "inseason" | "late";

export function weekRegime(week: number | null | undefined): WeekRegime {
  if (week == null || !Number.isFinite(week)) return "early";
  const w = Math.trunc(week);
  if (w <= 2) return "early";
  if (w >= 6 && w <= 12) return "inseason";
  if (w >= 13) return "late";
  return "standard";
}

export function sideThresholdsForWeek(
  week: number | null | undefined,
): SidePointThresholds {
  const regime = weekRegime(week);
  if (regime === "early") return EARLY_SIDE;
  if (regime === "inseason" || regime === "late") return INSEASON_SIDE;
  return STANDARD_SIDE;
}

export function totalThresholdsForWeek(
  week: number | null | undefined,
): TotalPointThresholds {
  if (weekRegime(week) === "early") return EARLY_TOTAL;
  return BASELINE_TOTAL;
}
