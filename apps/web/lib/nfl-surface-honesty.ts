/**
 * NFL enterprise leftover honesty stamps (copy/stamp only).
 *
 * Awards vs Futures and Depth Charts vs Camp can disagree. Label each
 * surface with its own source + as-of. Do not reconcile numbers, mint a
 * combined ranking, join odds that are not joined, rewrite camp notes,
 * or hide tiles. (Engineering doctrine — page strings below are subscriber
 * English only.)
 */

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
