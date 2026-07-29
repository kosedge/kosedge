/**
 * Selective NFL side/total/ML publish policy (mirrors model-service
 * nfl_side_total_publish_policy.py + nfl_moneyline_publish_policy.py).
 *
 * Default PASS. PLAY only when edge is in a historically productive band.
 * Spread LEAN band is disabled (settled ROI −14% in edge-bucket study).
 * Spread PLAY v2: [2.5, 7.0). Totals: sides-only launch (TOTAL_PLAY_ENABLED=false).
 * ML PLAY: requires spread PLAY + vig-aware EV ≥ 2%.
 * Preseason: NFL_PRESEASON_MODE=info blocks season PLAY on PRE games.
 */

export type NflPublishTag = "PLAY" | "LEAN" | "PASS";
export type NflPublishMarket = "spread" | "total";

export const SPREAD_PLAY_MIN = 2.5;
/** Half-open upper bound — |edge| ≥ 7 is PASS (mega-edge size-down). */
export const SPREAD_PLAY_MAX = 7.0;
export const TOTAL_PLAY_MIN = 2.5;
export const TOTAL_PLAY_MAX = 3.0;
/** Week-1 launch: confirmatory totals CLV RED — sides-only product. */
export const TOTAL_PLAY_ENABLED = false;
export const ML_MIN_EV = 0.02;
export const ML_POLICY_VERSION = "ml_from_spread_play_v1";

/** Product gate from ops artifact — RED forces PASS. */
export type NflProductGateStatus = "GREEN" | "YELLOW" | "RED";

export function isPreseasonSeasonType(seasonType?: string | null): boolean {
  if (!seasonType) return false;
  const token = seasonType.trim().toUpperCase();
  return (
    token === "PRE" ||
    token === "PRESEASON" ||
    token === "PRE_SEASON" ||
    token === "EXHIBITION"
  );
}

/** Default true (info desk). Pass false only for unit tests. */
export function isPreseasonInfoMode(
  mode: string | undefined = process.env.NFL_PRESEASON_MODE ?? "info",
): boolean {
  const m = (mode || "info").trim().toLowerCase();
  return ["info", "watch", "pass", "1", "true", "yes"].includes(m);
}

export function nflCandidateTag(
  market: NflPublishMarket,
  absEdge: number,
): NflPublishTag {
  const e = Math.abs(absEdge);
  if (market === "spread") {
    if (e >= SPREAD_PLAY_MIN && e < SPREAD_PLAY_MAX) return "PLAY";
    return "PASS";
  }
  if (!TOTAL_PLAY_ENABLED) return "PASS";
  if (e >= TOTAL_PLAY_MIN && e < TOTAL_PLAY_MAX) return "PLAY";
  return "PASS";
}

/**
 * Apply selective publish rules. Segment evidence is treated as pre-cleared
 * for spread PLAY bands shipped in nfl-edge-bucket-roi-study; RED
 * product gates still force PASS. Totals are sides-only at Week-1 launch.
 */
export function nflPublishTag(
  market: NflPublishMarket,
  absEdge: number | undefined | null,
  productGate: NflProductGateStatus = "YELLOW",
  seasonType?: string | null,
): { tag: NflPublishTag; stakeEligible: boolean; reason: string } {
  if (isPreseasonSeasonType(seasonType) && isPreseasonInfoMode()) {
    return {
      tag: "PASS",
      stakeEligible: false,
      reason: "preseason_info_desk",
    };
  }
  if (market === "total" && !TOTAL_PLAY_ENABLED) {
    return {
      tag: "PASS",
      stakeEligible: false,
      reason: "totals_sides_only_launch",
    };
  }
  if (absEdge == null || !Number.isFinite(absEdge)) {
    return { tag: "PASS", stakeEligible: false, reason: "missing_edge" };
  }
  const candidate = nflCandidateTag(market, absEdge);
  if (productGate === "RED" || candidate === "PASS") {
    return {
      tag: "PASS",
      stakeEligible: false,
      reason: productGate === "RED" ? "product_gate_red" : "edge_below_band",
    };
  }
  if (candidate === "PLAY") {
    return {
      tag: "PLAY",
      stakeEligible: true,
      reason: "edge_and_segment_cleared",
    };
  }
  return { tag: "PASS", stakeEligible: false, reason: "segment_evidence_failed" };
}

export function americanToDecimal(american: number): number {
  const a = Number(american);
  if (a === 0) return 1;
  if (a > 0) return 1 + a / 100;
  return 1 + 100 / Math.abs(a);
}

export function americanToImpliedProb(american: number): number {
  const a = Number(american);
  if (a === 0) return 0.5;
  if (a > 0) return 100 / (a + 100);
  return Math.abs(a) / (Math.abs(a) + 100);
}

/** Expected value of a 1-unit bet at American odds given model win probability. */
export function nflMlEvPerUnit(
  modelWinProb: number,
  americanOdds: number,
): number {
  const p = Math.max(0, Math.min(1, Number(modelWinProb)));
  const profitIfWin = americanToDecimal(americanOdds) - 1;
  return p * profitIfWin - (1 - p);
}

export function nflPublishMoneylineTag(args: {
  spreadTag: string;
  spreadStakeEligible: boolean;
  modelWinProb?: number | null;
  offeredAmerican?: number | null;
  productGate?: NflProductGateStatus;
  minEv?: number;
  seasonType?: string | null;
}): { tag: NflPublishTag; stakeEligible: boolean; reason: string; ev?: number } {
  if (isPreseasonSeasonType(args.seasonType) && isPreseasonInfoMode()) {
    return {
      tag: "PASS",
      stakeEligible: false,
      reason: "preseason_info_desk",
    };
  }
  const gate = args.productGate ?? "YELLOW";
  if (gate === "RED") {
    return { tag: "PASS", stakeEligible: false, reason: "product_gate_red" };
  }
  if (!args.spreadStakeEligible || String(args.spreadTag).toUpperCase() !== "PLAY") {
    return { tag: "PASS", stakeEligible: false, reason: "spread_not_play" };
  }
  if (
    args.modelWinProb == null ||
    !Number.isFinite(args.modelWinProb) ||
    args.offeredAmerican == null ||
    !Number.isFinite(args.offeredAmerican)
  ) {
    return { tag: "PASS", stakeEligible: false, reason: "missing_ml_inputs" };
  }
  const minEv = args.minEv ?? ML_MIN_EV;
  const ev = nflMlEvPerUnit(args.modelWinProb, args.offeredAmerican);
  if (ev < minEv) {
    return {
      tag: "PASS",
      stakeEligible: false,
      reason: "ml_ev_below_bar",
      ev: Math.round(ev * 10000) / 10000,
    };
  }
  return {
    tag: "PLAY",
    stakeEligible: true,
    reason: "spread_play_and_ml_ev_cleared",
    ev: Math.round(ev * 10000) / 10000,
  };
}
