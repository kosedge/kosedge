/**
 * Award-race display doctrine (2026-08-12):
 * `award_score` is a relative 0–1 model index (team success + stats + prior).
 * It is not P(award). Do not render % or “probability” until a path MC
 * chooses exactly one winner per sim and the field sums to ~100%.
 */

export const AWARD_SCORE_LABEL = "Award Score";

export const AWARD_SCORE_TITLE =
  "Relative model index (0–100). Not a probability — scores do not sum to 100.";

/** 0–1 API score → 0–100 index for display (no percent sign). */
export function awardScoreIndex(
  score: number | null | undefined,
): number | null {
  if (score == null || !Number.isFinite(score)) return null;
  return score * 100;
}

export function formatAwardScore(
  score: number | null | undefined,
): string {
  const index = awardScoreIndex(score);
  if (index == null) return "—";
  return index.toFixed(1);
}
