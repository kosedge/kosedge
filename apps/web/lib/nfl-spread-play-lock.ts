/**
 * Locked spread PLAY holdout — Ryan Kos 2026-09-03.
 * Doctrine: `/NFL_SPREAD_PLAY_LOCKED.md`
 * Holdout: `data/ops/nfl-play-only-holdout.md` · `spread_play_v2_cap7`
 *
 * Shared by publish policy + decision engine so subscriber surfaces cannot drift.
 */

export const SPREAD_PLAY_POLICY = "spread_play_v2_cap7";
/** Inclusive lower bound for spread PLAY. */
export const SPREAD_PLAY_MIN = 2.5;
/** Half-open upper bound — |edge| ≥ 7.0 is not PLAY in this band. */
export const SPREAD_PLAY_MAX = 7.0;

/** Totals PLAY remains sat until Ryan flips after a green unused holdout. */
export const TOTAL_PLAY_ENABLED = false;

export function spreadEdgeInPlayBand(
  absEdge: number | null | undefined,
): boolean {
  if (absEdge == null || !Number.isFinite(absEdge)) return false;
  const e = Math.abs(Number(absEdge));
  return e >= SPREAD_PLAY_MIN && e < SPREAD_PLAY_MAX;
}
