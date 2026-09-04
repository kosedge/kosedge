/**
 * Dead-tier honesty — hide unreachable badge / filter promises.
 *
 * Ryan default: when a tier cannot be earned under current constants, remove it
 * from subscriber filters / legends / empty-state promises. Do not flip stake
 * gates or raise confidence floors here — that is a separate product decision.
 *
 * Sport Standard publish tags (customer chrome): PLAY / LEAN / PASS only
 * (+ BEST VALUE only when reachable). ALERT / STAY AWAY / isBestBet /
 * STRONG PLAY / EXCEPTIONAL are internal decision-engine debt — map or hide
 * at this display layer; do not introduce Best Bet / Stay Away as publish tags.
 * Props-desk WATCH is props vocabulary, not Sport Standard game publish.
 *
 * Re-enable later:
 * - Prop PLAY: set model-service `PLAY_STAKE_ELIGIBLE = True` after a cleared
 *   holdout, then mirror `NFL_PROPS_PLAY_STAKE_ELIGIBLE` below.
 * - BEST VALUE / HIGH: raise `CONFIDENCE_TIER_BASE` ≥ HIGH cut (0.75) or lower
 *   the HIGH / BEST-BET cut so the tier is actually earnable early season.
 */

import type { ActionLabel, ConfidenceBand } from "@/lib/nfl-decision-engine";
import {
  CONFIDENCE_BEST_BET_MIN,
  CONFIDENCE_TIER_BASE,
} from "@/lib/nfl-tag-policy";

/**
 * Mirror of `services/model-service/.../nfl_prop_edge_policy.PLAY_STAKE_ELIGIBLE`.
 * Keep false until a deliberate stake-promotion PR. Do not flip in display PRs.
 */
export const NFL_PROPS_PLAY_STAKE_ELIGIBLE = false;

/** Prop PLAY tag / filter — unreachable while stake gate is off. */
export const PROP_PLAY_TIER_REACHABLE = NFL_PROPS_PLAY_STAKE_ELIGIBLE;

/**
 * Game-side HIGH band + BEST VALUE require score ≥ CONFIDENCE_BEST_BET_MIN (0.75).
 * Early-season tier base is 0.72 → neither is earnable without a designed bump.
 */
export const HIGH_CONFIDENCE_BAND_REACHABLE =
  CONFIDENCE_TIER_BASE + 1e-12 >= CONFIDENCE_BEST_BET_MIN;

export const BEST_VALUE_TIER_REACHABLE = HIGH_CONFIDENCE_BAND_REACHABLE;

/** Edges desk min-confidence chips — omit the HIGH cut while unreachable. */
export const EDGES_DESK_MIN_CONF_OPTIONS = (
  HIGH_CONFIDENCE_BAND_REACHABLE ? [0, 0.4, 0.6, 0.75] : [0, 0.4, 0.6]
) as readonly number[];

const ALL_ACTION_LABELS: readonly ActionLabel[] = [
  "PASS",
  "LEAN",
  "PLAY",
  "BEST VALUE",
  "ALERT",
  "STAY AWAY",
] as const;

const ALL_CONFIDENCE_BANDS: readonly ConfidenceBand[] = [
  "LOW",
  "MEDIUM",
  "HIGH",
] as const;

/** Action labels safe to promise in legends / filter chrome. */
export function reachableActionLabels(
  labels: readonly ActionLabel[] = ALL_ACTION_LABELS,
): ActionLabel[] {
  return labels.filter((label) => {
    if (label === "BEST VALUE") return BEST_VALUE_TIER_REACHABLE;
    // Legacy / non-Sport-Standard — never promise as publish tags.
    if (label === "ALERT" || label === "STAY AWAY") return false;
    return true;
  });
}

/** Confidence bands safe to promise in legends / filter chrome. */
export function reachableConfidenceBands(
  bands: readonly ConfidenceBand[] = ALL_CONFIDENCE_BANDS,
): ConfidenceBand[] {
  return bands.filter((band) => {
    if (band === "HIGH") return HIGH_CONFIDENCE_BAND_REACHABLE;
    return true;
  });
}

/**
 * Subscriber badge: Sport Standard publish vocabulary only.
 * - Unreachable BEST VALUE → PLAY (no gold badge promise).
 * - ALERT / STAY AWAY → PASS (legacy decision-engine labels; not publish tags).
 * Engine thresholds / ActionLabel union are unchanged.
 */
export function displayActionLabel(
  label: ActionLabel | null | undefined,
): ActionLabel | null {
  if (label == null) return null;
  if (label === "ALERT" || label === "STAY AWAY") return "PASS";
  if (label === "BEST VALUE" && !BEST_VALUE_TIER_REACHABLE) return "PLAY";
  return label;
}

/** Prop tag filter options — omit PLAY while stake-ineligible. */
export function reachablePropTagFilters(): readonly (
  | "WATCH"
  | "PASS"
  | "LEAN"
  | "PLAY"
)[] {
  if (PROP_PLAY_TIER_REACHABLE) {
    return ["PLAY", "WATCH", "LEAN", "PASS"] as const;
  }
  return ["WATCH", "LEAN", "PASS"] as const;
}

export const DEAD_TIER_OPS_BLURB =
  "Hidden tiers: prop PLAY (PLAY_STAKE_ELIGIBLE=false); game BEST VALUE / HIGH (tier base 0.72 < HIGH cut 0.75). Re-enable only as a product decision — not from display PRs.";
