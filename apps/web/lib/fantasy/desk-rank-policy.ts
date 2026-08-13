/**
 * Fantasy Draft Desk rank policy — display order vs honest Model column.
 *
 * Model rank (`rankOverall`) and points stay raw VOR / season-engine math.
 * Board **Rk** is a value-aware sort so the desk is not silently ±10 off
 * consensus unless we are taking a labeled side.
 *
 * Diagnosis (2026-08-13): sorting on raw model *points* floods a 1QB board
 * with QBs (Burrow 375 pts vs CMC 318). The shipped key is therefore
 * **rank-space**, the same quantity Model # already uses:
 *
 *   board_key = modelRank + reach_penalty_slots − wait_bubble_slots
 *   (lower = earlier on the board)
 *
 *   reach_penalty_slots = max(0, ADP − modelRank − 12) × 0.85
 *   wait_bubble_slots   = min(max(0, modelRank − ADP), 24) × 0.35
 *   QB extra slots      = max(0, ADP − modelRank − 24) × 0.50
 *
 * Reaching ADP by 1+ rounds is penalized. Waiting on a model favorite may
 * bubble modestly. Unmatched / cross-format ADP is not blended (key =
 * modelRank). QB extra aligns with Mock late-QB2 suppress.
 */

export const DESK_RANK_POLICY = {
  /** 12-team snake round size. */
  roundSize: 12,
  /** One round of model-ahead is free (not treated as a board reach). */
  reachFreePicks: 12,
  /** Board slots added per pick beyond the free round. */
  reachPenaltyPerPick: 0.85,
  /** Modest bubble when ADP is ahead of model rank (market favorite). */
  waitBubblePerPick: 0.35,
  waitBubbleCapPicks: 24,
  /** Extra QB suppress when model ranks a QB 2+ rounds ahead of ADP. */
  qbReachExtraAfterPicks: 24,
  qbReachExtraPerPick: 0.5,
} as const;

export type DeskRankable = {
  rankOverall: number;
  position: string;
  adp: number | null;
  adpMatchConfidence: "high" | "cross_format" | null;
};

/**
 * Lower = earlier on the board. Does not mutate Model rank or points.
 * `deskSortScore` is the descending-sort form (−key) for reuse next to
 * value-aware recs.
 */
export function deskBoardKey(row: DeskRankable): number {
  const rank = Number(row.rankOverall) || 0;
  const adp = row.adp;
  if (
    adp == null ||
    !Number.isFinite(adp) ||
    row.adpMatchConfidence !== "high"
  ) {
    return rank;
  }

  const modelAhead = adp - rank;
  let key = rank;

  if (modelAhead > DESK_RANK_POLICY.reachFreePicks) {
    key +=
      (modelAhead - DESK_RANK_POLICY.reachFreePicks) *
      DESK_RANK_POLICY.reachPenaltyPerPick;
  } else if (modelAhead < 0) {
    const wait = Math.min(-modelAhead, DESK_RANK_POLICY.waitBubbleCapPicks);
    key -= wait * DESK_RANK_POLICY.waitBubblePerPick;
  }

  const pos = row.position.toUpperCase();
  if (
    pos === "QB" &&
    modelAhead > DESK_RANK_POLICY.qbReachExtraAfterPicks
  ) {
    key +=
      (modelAhead - DESK_RANK_POLICY.qbReachExtraAfterPicks) *
      DESK_RANK_POLICY.qbReachExtraPerPick;
  }

  return key;
}

/** Higher = stronger board slot. Inverse of `deskBoardKey`. */
export function deskSortScore(row: DeskRankable): number {
  return -deskBoardKey(row);
}

export function applyDeskRankPolicy<T extends DeskRankable>(
  rows: T[],
): Array<T & { deskOrder: number }> {
  return [...rows]
    .sort((a, b) => {
      const keyDiff = deskBoardKey(a) - deskBoardKey(b);
      if (keyDiff !== 0) return keyDiff;
      if (a.rankOverall !== b.rankOverall) {
        return a.rankOverall - b.rankOverall;
      }
      return 0;
    })
    .map((row, idx) => ({ ...row, deskOrder: idx + 1 }));
}

export function boardRank(row: {
  deskOrder?: number;
  rankOverall: number;
}): number {
  return row.deskOrder ?? row.rankOverall;
}
