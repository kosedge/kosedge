/**
 * Weekly `/props/board` shares the player-production spine with fantasy.
 * LIVE = research→fire for means/bands + optional edge vs market.
 * Not a stake-tag / CLV-proven props book. Rollback: set false.
 *
 * 2025 = calibrated 3C control. 2026 = preseason grain (elevated rec gap).
 */
export const NFL_WEEKLY_PROPS_LIVE = true;

export const NFL_WEEKLY_PROPS_PATH_COHERENT: "yes" | "gated" =
  NFL_WEEKLY_PROPS_LIVE ? "yes" : "gated";

export const NFL_WEEKLY_PROPS_GATE_TITLE =
  "Weekly player props not live — season desk only";

export const NFL_WEEKLY_PROPS_GATE_BODY =
  "Week 1 player props are gated until the weekly box sim is rebuilt on the same depth and production path as season projections. Season totals, fantasy ranks, and Edge Board game lines stay on the desk.";

/** Visible methods — not 3C-tight 2026 receiving, not a bet card. */
export const NFL_WEEKLY_PROPS_METHODS = [
  "Weekly player means from the production spine (player-production-v3-phase3c). Structure cal is edge math only.",
  "Season totals = sum of weekly means, cap 17 games. Fantasy uses the same means.",
  "Playing time follows the depth chart: QB3 / WR4+ / RB3+ are not treated as starters.",
  "2026 preseason: receiving totals are elevated vs pass (roster-width grain). Not the same tightness as the 2025 control (gap ~0.10).",
  "Numbers and market edge when a book is joined. No PLAY / LEAN stake tags. Not a CLV-proven props book.",
] as const;
