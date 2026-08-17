/**
 * CFB research-surface labeling.
 * Season Model / Project Game are MODEL desks. August must not read as a
 * live betting board. Edge Board CFB publishes KEI vs market; Model stays research.
 */

import type { TruthUiState } from "@/lib/truth-ui-state";

export const CFB_PRODUCT_SEASON = 2026;

/**
 * Inclusive last calendar day treated as preseason (day before Week 0).
 * 2026 FBS Week 0 / first slate is Saturday 2026-08-29.
 */
export const CFB_PRESEASON_CUTOFF_ISO: Record<number, string> = {
  2026: "2026-08-28",
};

const DEFAULT_PRESEASON_CUTOFF_MD = "08-28";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function cfbPreseasonCutoffIso(season: number): string {
  return (
    CFB_PRESEASON_CUTOFF_ISO[season] ?? `${season}-${DEFAULT_PRESEASON_CUTOFF_MD}`
  );
}

export function isCfbCalendarPreseason(
  season: number = CFB_PRODUCT_SEASON,
  now: Date = new Date(),
): boolean {
  return isoDate(now) <= cfbPreseasonCutoffIso(season);
}

/** Season Model / Project Game: always MODEL; PRESEASON until Week 0. Never LIVE. */
export function cfbModelDeskTruthStates(
  now: Date = new Date(),
  season: number = CFB_PRODUCT_SEASON,
): TruthUiState[] {
  return isCfbCalendarPreseason(season, now)
    ? ["PRESEASON", "MODEL"]
    : ["MODEL"];
}

export function cfbModelDeskHonestyNote(
  now: Date = new Date(),
  season: number = CFB_PRODUCT_SEASON,
): string {
  const pre = isCfbCalendarPreseason(season, now);
  const head = pre
    ? "PRESEASON · MODEL research"
    : "MODEL research";
  return `${head} — Model is not the published handicap. KEI is the published line; Edge / Tag = KEI vs market.`;
}
