/**
 * Value-aware draft recommendations — action surface only.
 *
 * Rankings stay raw Model rank. This module scores Builder / Mock *advice*
 * (take / wait / reach). Not an “optimal pick” claim.
 *
 * Formula (per candidate, higher = stronger recommendation):
 *
 *   score = (VOR + need − reach_penalty + wait_bonus) × needMult + scarcity
 *
 *   VOR            = clamp(valueOverReplacement, 0, VOR_CAP) × VOR_SCALE
 *   need           = unfilled starter slots at the position
 *   reach_penalty  = picks you would take before ADP (and model-ahead vs ADP
 *                    beyond one round), reduced only for elite + cliff + hole
 *   wait_bonus     = positive Value Δ when ADP is still later than this pick
 *   needMult       = 1 + min(NEED_CAP, slots × NEED_SLOT_BOOST)
 *
 * Model # and ADP stay on the row untouched. Tunable knobs below.
 */

import { rosterNeeds } from "@/lib/fantasy/team-builder";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

/**
 * Hard cap vs ADP for user-facing take/wait CTAs (12-team round).
 * Value Δ and High deviation flags may still show larger gaps.
 */
export const MAX_RECOMMEND_RANK_DELTA = 12;

/** Tunable recommendation knobs — adjust without touching UI. */
export const VALUE_AWARE_WEIGHTS = {
  /** Cap on VOR contribution so one outlier QB cannot swamp the board. */
  vorCap: 250,
  /** Points per VOR (starter RB ~130 VOR → ~15.6). */
  vorScale: 0.12,
  /** Flat points per unfilled starter slot at the player's position. */
  needPointsPerSlot: 8,
  /** Base model-strength offset before rank decay (kept as a soft prior). */
  modelRankBase: 40,
  /** Points subtracted per model rank slot (lower rank = stronger). */
  modelRankPerPoint: 0.12,
  /** Multiplier on valueDelta when player is a market discount vs pick. */
  discountBonusScale: 1.2,
  /** Minimum valueDelta before discount bonus applies. */
  discountMinDelta: 4,
  /** Picks before ADP where reach penalty starts (fair zone). */
  reachSoftThreshold: 6,
  /** Penalty per pick of early reach (pick materially before ADP). */
  reachPenaltyPerPick: 0.85,
  /** Model rank at or above which a player counts as elite for reach override. */
  eliteRankThreshold: 12,
  /** Minimum scarcity score to allow reduced reach penalty. */
  reachOverrideScarcityMin: 10,
  /** Minimum unfilled starter slots (need score) for reach override. */
  reachOverrideNeedMin: 2,
  /** Reach penalty multiplier when override applies (0–1). */
  reachOverridePenaltyScale: 0.25,
  /** Added to need multiplier per unfilled starter slot at position. */
  needBoostPerSlot: 0.08,
  /** Cap on need multiplier. */
  needBoostMax: 1.45,
  /** Scarcity bonus when ≤1 top options remain before cliff. */
  scarcityEliteCliff: 18,
  /** Scarcity bonus when ≤3 top options remain. */
  scarcityModerateCliff: 10,
  /** TE-specific mild cliff bonus. */
  scarcityMildCliff: 6,
  /** Window (picks) where ADP urgency triggers "take now". */
  adpUrgencyWindow: 4,
  /** Picks ahead of ADP where "wait" hint applies with strong valueDelta. */
  waitAdpLeadMin: 8,
  /** Do not Wait-CTA lottery ADP (Gesicki-class). Three 12-team rounds. */
  waitHorizonPicks: 36,
} as const;

export type SuggestionTiming = "take_now" | "wait" | "reach" | "fair";

export const DRAFT_ADVICE_COPY = {
  takeAligned: "Take now — model and market aligned",
  takeValue: "Take now — value at this pick",
  wait: "Wait — available later by ADP",
  reach: "Reach — only if need is extreme",
} as const;

export type ValueAwareSuggestion = {
  row: FantasyDeskRow;
  score: number;
  timing: SuggestionTiming;
  /** Short helper for mobile clock UI; null when nothing actionable. */
  timingHint: string | null;
};

export type ValueAwareContext = {
  /** Current overall pick (1-based). Omit in builder for static value mode. */
  pickOverall?: number;
  roster: FantasyDeskRow[];
  available: FantasyDeskRow[];
  needs?: Record<string, number>;
};

function vorTerm(row: FantasyDeskRow): number {
  const w = VALUE_AWARE_WEIGHTS;
  const vor = Number(row.valueOverReplacement) || 0;
  return Math.max(0, Math.min(w.vorCap, vor)) * w.vorScale;
}

function needTerm(row: FantasyDeskRow, needs: Record<string, number>): number {
  return positionalNeedScore(row, needs) * VALUE_AWARE_WEIGHTS.needPointsPerSlot;
}

function modelAheadReachPenalty(row: FantasyDeskRow): number {
  const w = VALUE_AWARE_WEIGHTS;
  if (row.adp == null || !Number.isFinite(row.adp)) return 0;
  if (row.adpMatchConfidence !== "high") return 0;
  const modelAhead = row.adp - row.rankOverall;
  const extra = modelAhead - MAX_RECOMMEND_RANK_DELTA;
  if (extra <= 0) return 0;
  return extra * w.reachPenaltyPerPick;
}

function positionalNeedScore(
  row: FantasyDeskRow,
  needs: Record<string, number>,
): number {
  const pos = row.position.toUpperCase();
  const direct = needs[pos] ?? 0;
  if (direct > 0) return direct;
  if (
    (needs.FLEX ?? 0) > 0 &&
    ["RB", "WR", "TE"].includes(pos)
  ) {
    return 1;
  }
  return 0;
}

function scarcityBonus(
  row: FantasyDeskRow,
  available: FantasyDeskRow[],
  pickOverall: number | undefined,
): number {
  const w = VALUE_AWARE_WEIGHTS;
  const pos = row.position.toUpperCase();
  const horizon = pickOverall ?? row.rankOverall + 40;
  const pool = available
    .filter((r) => r.position.toUpperCase() === pos)
    .sort((a, b) => a.rankOverall - b.rankOverall);
  if (pool.length === 0) return 0;
  const topLeft = pool.filter((r) => r.rankOverall <= horizon + 40).length;
  if (topLeft <= 1) return w.scarcityEliteCliff;
  if (topLeft <= 3) return w.scarcityModerateCliff;
  if (pos === "TE" && topLeft <= 5) return w.scarcityMildCliff;
  return 0;
}

function needMultiplier(
  row: FantasyDeskRow,
  needs: Record<string, number>,
): number {
  const w = VALUE_AWARE_WEIGHTS;
  const needScore = positionalNeedScore(row, needs);
  return Math.min(w.needBoostMax, 1 + needScore * w.needBoostPerSlot);
}

function discountBonus(
  row: FantasyDeskRow,
  pickOverall: number | undefined,
): number {
  const w = VALUE_AWARE_WEIGHTS;
  if (row.valueDelta == null || row.valueDelta < w.discountMinDelta) return 0;
  if (pickOverall == null) {
    return row.valueDelta * w.discountBonusScale * 0.7;
  }
  const adp = row.adp;
  if (adp == null) return row.valueDelta * w.discountBonusScale * 0.5;
  if (adp > pickOverall + w.reachSoftThreshold) {
    return row.valueDelta * w.discountBonusScale;
  }
  if (adp > pickOverall) {
    return row.valueDelta * w.discountBonusScale * 0.35;
  }
  return 0;
}

export function reachPenalty(
  row: FantasyDeskRow,
  pickOverall: number | undefined,
  needScore: number,
  scarcity: number,
): number {
  const w = VALUE_AWARE_WEIGHTS;
  if (pickOverall == null || row.adp == null) return 0;
  const earlyBy = row.adp - pickOverall;
  if (earlyBy >= w.reachSoftThreshold) return 0;
  const reachAmount = w.reachSoftThreshold - earlyBy;
  if (reachAmount <= 0) return 0;

  const eliteReachOverride =
    row.rankOverall <= w.eliteRankThreshold &&
    scarcity >= w.reachOverrideScarcityMin &&
    needScore >= w.reachOverrideNeedMin;

  const scale = eliteReachOverride ? w.reachOverridePenaltyScale : 1;
  return reachAmount * w.reachPenaltyPerPick * scale;
}

/** Inspectable per-player score — model rank and ADP stay untouched on the row. */
export function scoreValueAwarePlayer(
  row: FantasyDeskRow,
  ctx: ValueAwareContext,
): ValueAwareSuggestion {
  const needs = ctx.needs ?? rosterNeeds(ctx.roster);
  const needScore = positionalNeedScore(row, needs);
  const scarcity = scarcityBonus(row, ctx.available, ctx.pickOverall);

  const vor = vorTerm(row);
  const need = needTerm(row, needs);
  const discount = discountBonus(row, ctx.pickOverall);
  const pickReach = reachPenalty(row, ctx.pickOverall, needScore, scarcity);
  const modelReach = modelAheadReachPenalty(row);
  const reach = pickReach + modelReach;
  const needMult = needMultiplier(row, needs);
  const rankPrior = Math.max(
    0,
    VALUE_AWARE_WEIGHTS.modelRankBase -
      row.rankOverall * VALUE_AWARE_WEIGHTS.modelRankPerPoint,
  );

  const score =
    (vor + need + rankPrior + discount - reach) * needMult + scarcity;
  const { timing, timingHint } = computeTiming(
    row,
    ctx.pickOverall,
    needs,
    scarcity,
    pickReach,
  );

  return { row, score, timing, timingHint };
}

/** Spots before ADP this pick would be (positive = reach vs market). */
export function adpReachSpots(
  row: FantasyDeskRow,
  pickOverall: number | undefined,
): number | null {
  if (pickOverall == null || row.adp == null || !Number.isFinite(row.adp)) {
    return null;
  }
  return row.adp - pickOverall;
}

/** True when a take-now / reach CTA would exceed the ±12 ADP policy. */
export function exceedsRecommendReachCap(
  row: FantasyDeskRow,
  pickOverall: number | undefined,
): boolean {
  const spots = adpReachSpots(row, pickOverall);
  if (spots == null) {
    if (pickOverall == null && row.valueDelta != null) {
      return Math.abs(row.valueDelta) > MAX_RECOMMEND_RANK_DELTA;
    }
    return false;
  }
  return spots > MAX_RECOMMEND_RANK_DELTA;
}

export function computeTiming(
  row: FantasyDeskRow,
  pickOverall: number | undefined,
  needs: Record<string, number>,
  scarcity: number,
  reachAmount: number,
): { timing: SuggestionTiming; timingHint: string | null } {
  const w = VALUE_AWARE_WEIGHTS;
  const adp = row.adp;
  const pos = row.position.toUpperCase();
  const hasNeed = positionalNeedScore(row, needs) > 0;
  const overCap = exceedsRecommendReachCap(row, pickOverall);

  if (pickOverall == null) {
    if (overCap) {
      return { timing: "fair", timingHint: null };
    }
    if (row.valueDelta != null && row.valueDelta >= 8) {
      return { timing: "wait", timingHint: DRAFT_ADVICE_COPY.wait };
    }
    if (row.valueDelta != null && row.valueDelta <= -8) {
      return { timing: "take_now", timingHint: DRAFT_ADVICE_COPY.takeAligned };
    }
    return { timing: "fair", timingHint: null };
  }

  if (adp == null) {
    if (hasNeed && row.rankOverall <= 36) {
      return { timing: "take_now", timingHint: DRAFT_ADVICE_COPY.takeAligned };
    }
    return { timing: "fair", timingHint: null };
  }

  const adpLaterBy = adp - pickOverall;
  const inWaitHorizon =
    adpLaterBy > w.waitAdpLeadMin && adpLaterBy <= w.waitHorizonPicks;

  // Wait can fire past the ±12 take/reach cap — that's the whole point of
  // "model 18 / ADP 35". Lottery ADP (beyond three rounds) stays unlabeled.
  if (
    row.valueDelta != null &&
    row.valueDelta >= 8 &&
    inWaitHorizon
  ) {
    return { timing: "wait", timingHint: DRAFT_ADVICE_COPY.wait };
  }

  if (
    row.valueDelta != null &&
    row.valueDelta >= w.discountMinDelta &&
    adpLaterBy > w.reachSoftThreshold + 4 &&
    adpLaterBy <= w.waitHorizonPicks
  ) {
    return { timing: "wait", timingHint: DRAFT_ADVICE_COPY.wait };
  }

  // Past ±12 vs ADP: never a Take or Reach CTA.
  if (overCap) {
    return { timing: "fair", timingHint: null };
  }

  const extremeNeedReach =
    hasNeed &&
    scarcity >= w.reachOverrideScarcityMin &&
    row.rankOverall <= w.eliteRankThreshold + 12 &&
    adp > pickOverall + w.adpUrgencyWindow;

  if (extremeNeedReach) {
    return { timing: "reach", timingHint: DRAFT_ADVICE_COPY.reach };
  }

  if (adp <= pickOverall + w.adpUrgencyWindow) {
    const hint =
      row.valueDelta != null && row.valueDelta >= w.discountMinDelta
        ? DRAFT_ADVICE_COPY.takeValue
        : DRAFT_ADVICE_COPY.takeAligned;
    return { timing: "take_now", timingHint: hint };
  }

  if (
    hasNeed &&
    scarcity >= w.reachOverrideScarcityMin &&
    row.rankOverall <= w.eliteRankThreshold + 12 &&
    adp <= pickOverall + w.reachSoftThreshold + 10
  ) {
    return { timing: "take_now", timingHint: DRAFT_ADVICE_COPY.takeValue };
  }

  if (reachAmount > 0 && !hasNeed && scarcity < w.reachOverrideScarcityMin) {
    return { timing: "wait", timingHint: DRAFT_ADVICE_COPY.wait };
  }

  if (Math.abs(pickOverall - adp) <= w.reachSoftThreshold) {
    return { timing: "fair", timingHint: null };
  }

  if (pos === "QB" && (needs.QB ?? 0) === 0 && pickOverall < adp - 10) {
    return { timing: "wait", timingHint: DRAFT_ADVICE_COPY.wait };
  }

  return { timing: "fair", timingHint: null };
}

function rankSuggestions(
  available: FantasyDeskRow[],
  ctx: ValueAwareContext,
  limit: number,
): ValueAwareSuggestion[] {
  return available
    .map((row) => scoreValueAwarePlayer(row, ctx))
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.row.rankOverall - b.row.rankOverall;
    })
    .slice(0, limit);
}

/** Value-aware best available — optimizes model strength + price timing. */
export function bestAvailableByValueAware(
  available: FantasyDeskRow[],
  ctx: ValueAwareContext,
  limit = 5,
): ValueAwareSuggestion[] {
  const pool = available.filter(
    (row) => row.adp != null || row.rankOverall > 0,
  );
  return rankSuggestions(pool, ctx, limit);
}

/** Value-aware need-first — fills roster holes then ranks by value-aware score. */
export function bestAvailableByNeedAware(
  available: FantasyDeskRow[],
  ctx: ValueAwareContext,
  limit = 5,
): ValueAwareSuggestion[] {
  const needs = ctx.needs ?? rosterNeeds(ctx.roster);
  const priority = Object.entries(needs)
    .filter(([pos, n]) => n > 0 && pos !== "FLEX")
    .sort((a, b) => b[1] - a[1])
    .map(([pos]) => pos);

  const flexNeed = (needs.FLEX ?? 0) > 0;
  const scored = available.map((row) => scoreValueAwarePlayer(row, ctx));
  const seen = new Set<string>();
  const out: ValueAwareSuggestion[] = [];

  const pushMatching = (predicate: (s: ValueAwareSuggestion) => boolean) => {
    for (const s of scored.sort((a, b) => b.score - a.score)) {
      if (out.length >= limit) break;
      if (seen.has(s.row.playerId)) continue;
      if (!predicate(s)) continue;
      out.push(s);
      seen.add(s.row.playerId);
    }
  };

  for (const pos of priority) {
    pushMatching((s) => s.row.position.toUpperCase() === pos);
  }
  if (flexNeed) {
    pushMatching((s) =>
      ["RB", "WR", "TE"].includes(s.row.position.toUpperCase()),
    );
  }
  pushMatching(() => true);
  return out.slice(0, limit);
}

export function draftAdviceClass(timing: SuggestionTiming): string {
  if (timing === "take_now") return "text-kos-gold";
  if (timing === "wait") return "text-sky-300/90";
  if (timing === "reach") return "text-rose-300/90";
  return "text-kos-text/45";
}
