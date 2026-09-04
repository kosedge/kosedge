/**
 * NFL enterprise leftover honesty stamps (copy/stamp only).
 *
 * Awards vs Futures and Depth Charts vs Camp can disagree. Label each
 * surface with its own source + as-of. Do not reconcile numbers, mint a
 * combined ranking, join odds that are not joined, rewrite camp notes,
 * or hide tiles. (Engineering doctrine — page strings below are subscriber
 * English only.)
 */

import {
  NFL_DEPTH_PACK_AS_OF,
  NFL_DEPTH_PACK_MAX_AGE_DAYS,
  isPackagedDepthStale,
} from "@/lib/nfl-depth-pack-freshness";

/** Awards board — model award-score snapshot, not Futures tiles. */
export const NFL_AWARDS_SOURCE_NAME = "Model award-score snapshot";

export const NFL_AWARDS_SOURCE_STAMP =
  "Source: model award-score snapshot from last materialize. Separate from Futures (different ranking / vintage). Player award odds not joined.";

/** Futures hub — season sim / spine, not Awards award-score. */
export const NFL_FUTURES_SOURCE_NAME = "Season sim / player-production spine";

export const NFL_FUTURES_SOURCE_STAMP =
  "Source: season sim / player-production spine. Separate from Awards. Leader odds not joined.";

/** Depth charts — packaged/model chart, not live Camp Desk. */
export const NFL_DEPTH_SOURCE_NAME = "Packaged model depth chart";

export const NFL_DEPTH_SOURCE_STAMP =
  "Source: packaged model depth chart — not live Camp Desk. Named QB1, IR, and claims live on Camp Desk.";

export const NFL_DEPTH_NOT_LIVE_CAMP_PHRASE = "not live Camp Desk";

/** Pack calendar as-of for depth / QB surfaces (not season-week truth). */
export function nflDepthPackAsOfLine(
  asOf: string = NFL_DEPTH_PACK_AS_OF,
): string {
  return `Pack as-of ${asOf}`;
}

/**
 * Subscriber stamp for depth/QB pack freshness.
 * When past max_age_days_camp_season, fail closed — point to Camp Desk.
 */
export function nflDepthPackFreshnessStamp(
  now: Date = new Date(),
  asOf: string = NFL_DEPTH_PACK_AS_OF,
  maxAgeDays: number = NFL_DEPTH_PACK_MAX_AGE_DAYS,
): string {
  const base = `${NFL_DEPTH_SOURCE_STAMP} ${nflDepthPackAsOfLine(asOf)}.`;
  if (!isPackagedDepthStale(now, asOf, maxAgeDays)) {
    return `${base} Freshness window ${maxAgeDays} days.`;
  }
  return `${base} Pack past ${maxAgeDays}-day camp freshness — QB roles may be stale; named QB1 / IR / claims on Camp Desk.`;
}
