/**
 * KosEdge Draft Rank — model order with a hard ADP reach cap.
 *
 * Rule: sort by our rank; never place someone more than ~1 round above ADP.
 *
 *   1. Start at model rank (projection / points order).
 *   2. If model rank is more than `reachCapPicks` before ADP → cap at ADP − cap
 *      (four-round reaches never sit at model rank on this board).
 *   3. If ADP is ahead of model → mild bump up (still sorted by adjusted rank).
 *   4. Assign deskOrder 1…N from the adjusted list.
 *
 * Unmatched / cross-format ADP → model rank only (no invented blend).
 */

import type { SuggestionTiming } from "@/lib/fantasy/value-aware-recs";

export const DESK_RANK_POLICY = {
  /** 12-team snake round size. */
  roundSize: 12,
  /**
   * Hard max picks model can rank ahead of ADP on the draft board.
   * 12 picks ≈ one round; tunable to 15–18 for 1.5 rounds.
   */
  reachCapPicks: 12,
  /** Small reach zone — badge Reach, still allowed at model rank. */
  reachBadgeMinPicks: 6,
  /** Market ahead of model — Value badge threshold. */
  valueBadgeMinPicks: 8,
  /** Mild bump per pick when market ADP is ahead of model. */
  valueBumpPerPick: 0.35,
  /** Cap picks considered for value bump. */
  valueBumpCapPicks: 18,
} as const;

export type DeskRankable = {
  rankOverall: number;
  position: string;
  adp: number | null;
  adpMatchConfidence: "high" | "cross_format" | null;
};

/**
 * Lower = earlier on the board. Does not mutate model rank.
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

  if (modelAhead > DESK_RANK_POLICY.reachCapPicks) {
    return adp - DESK_RANK_POLICY.reachCapPicks;
  }

  if (modelAhead < 0) {
    const marketAhead = -modelAhead;
    const bump = Math.min(marketAhead, DESK_RANK_POLICY.valueBumpCapPicks);
    return rank - bump * DESK_RANK_POLICY.valueBumpPerPick;
  }

  return rank;
}

/** True when model rank violates the hard reach cap vs ADP. */
export function isReachCapped(row: DeskRankable): boolean {
  const adp = row.adp;
  if (
    adp == null ||
    !Number.isFinite(adp) ||
    row.adpMatchConfidence !== "high"
  ) {
    return false;
  }
  return adp - row.rankOverall > DESK_RANK_POLICY.reachCapPicks;
}

/** Picks model ranks ahead of ADP (positive = model earlier). */
export function modelAheadOfAdp(row: DeskRankable): number | null {
  const adp = row.adp;
  if (
    adp == null ||
    !Number.isFinite(adp) ||
    row.adpMatchConfidence !== "high"
  ) {
    return null;
  }
  return adp - row.rankOverall;
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

export function draftRank(row: {
  deskOrder?: number;
  rankOverall: number;
}): number {
  return row.deskOrder ?? row.rankOverall;
}

/** @alias draftRank */
export const boardRank = draftRank;

export type DeskDraftBadgeLabel = "Fair" | "Reach" | "Value" | "Wait" | "—";

/** ≤3-word badge for the draft board row. */
export function deskDraftBadge(row: DeskRankable): {
  timing: SuggestionTiming;
  label: DeskDraftBadgeLabel;
} {
  const ahead = modelAheadOfAdp(row);
  if (ahead == null) {
    return { timing: "fair", label: "—" };
  }
  if (ahead > DESK_RANK_POLICY.reachCapPicks) {
    return { timing: "wait", label: "Wait" };
  }
  if (ahead >= DESK_RANK_POLICY.reachBadgeMinPicks) {
    return { timing: "reach", label: "Reach" };
  }
  if (ahead <= -DESK_RANK_POLICY.valueBadgeMinPicks) {
    return { timing: "take_now", label: "Value" };
  }
  return { timing: "fair", label: "Fair" };
}

/**
 * No matched player’s adjusted board slot sits more than `reachCapPicks` before ADP.
 */
export function assertNoHardReachViolations(rows: DeskRankable[]): void {
  for (const row of rows) {
    const adp = row.adp;
    if (
      adp == null ||
      !Number.isFinite(adp) ||
      row.adpMatchConfidence !== "high"
    ) {
      continue;
    }
    const slot = deskBoardKey(row);
    const reach = adp - slot;
    if (reach > DESK_RANK_POLICY.reachCapPicks) {
      throw new Error(
        `reach cap violated: model ${row.rankOverall} / ADP ${adp} / slot ${slot}`,
      );
    }
  }
}
