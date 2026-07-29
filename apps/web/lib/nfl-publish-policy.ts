/**
 * Selective NFL side/total publish policy (mirrors model-service
 * nfl_side_total_publish_policy.py).
 *
 * Default PASS. PLAY only when edge is in a historically productive band.
 * Spread LEAN band is disabled (settled ROI −14% in edge-bucket study).
 * Spread PLAY v2: [2.5, 7.0). Totals PLAY only in [2.5, 3.0).
 */

export type NflPublishTag = "PLAY" | "LEAN" | "PASS";
export type NflPublishMarket = "spread" | "total";

export const SPREAD_PLAY_MIN = 2.5;
/** Half-open upper bound — |edge| ≥ 7 is PASS (mega-edge size-down). */
export const SPREAD_PLAY_MAX = 7.0;
export const TOTAL_PLAY_MIN = 2.5;
export const TOTAL_PLAY_MAX = 3.0;

/** Product gate from ops artifact — RED forces PASS. */
export type NflProductGateStatus = "GREEN" | "YELLOW" | "RED";

export function nflCandidateTag(
  market: NflPublishMarket,
  absEdge: number,
): NflPublishTag {
  const e = Math.abs(absEdge);
  if (market === "spread") {
    if (e >= SPREAD_PLAY_MIN && e < SPREAD_PLAY_MAX) return "PLAY";
    return "PASS";
  }
  if (e >= TOTAL_PLAY_MIN && e < TOTAL_PLAY_MAX) return "PLAY";
  return "PASS";
}

/**
 * Apply selective publish rules. Segment evidence is treated as pre-cleared
 * for spread/total PLAY bands shipped in nfl-edge-bucket-roi-study; RED
 * product gates still force PASS.
 */
export function nflPublishTag(
  market: NflPublishMarket,
  absEdge: number | undefined | null,
  productGate: NflProductGateStatus = "YELLOW",
): { tag: NflPublishTag; stakeEligible: boolean; reason: string } {
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
  // Locked study: spread PLAY and narrow total PLAY cleared ATS.
  if (candidate === "PLAY") {
    return {
      tag: "PLAY",
      stakeEligible: true,
      reason: "edge_and_segment_cleared",
    };
  }
  return { tag: "PASS", stakeEligible: false, reason: "segment_evidence_failed" };
}
