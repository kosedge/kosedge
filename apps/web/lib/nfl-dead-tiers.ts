/**
 * Dead-tier honesty — hide unreachable badge / filter promises.
 *
 * Ryan default: when a tier cannot be earned under current constants, remove it
 * from subscriber filters / legends / empty-state promises. Do not flip stake
 * gates or raise confidence floors here — that is a separate product decision.
 *
 * Sport Standard publish tags (customer chrome / API serialize): PLAY / LEAN / PASS
 * only. Best Value ActionLabel only when BEST_VALUE_TIER_REACHABLE (actually
 * earnable / would render) — otherwise quarantine → PLAY. Flagged debt never
 * paints: ALERT, STAY AWAY, WATCH, isBestBet / Best Bet, STRONG PLAY, EXCEPTIONAL.
 * Engine unions stay intact; no PLAY flip / remat / Sport Standard redesign.
 *
 * Re-enable later:
 * - Prop PLAY: set model-service `PLAY_STAKE_ELIGIBLE = True` after a cleared
 *   holdout, then mirror `NFL_PROPS_PLAY_STAKE_ELIGIBLE` below.
 * - BEST VALUE / HIGH: raise `CONFIDENCE_TIER_BASE` ≥ HIGH cut (0.75) or lower
 *   the HIGH / BEST-BET cut so the tier is actually earnable early season.
 */

import type {
  ActionLabel,
  ConfidenceBand,
  PointGrade,
} from "@/lib/nfl-decision-engine";
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
 * - Unreachable BEST VALUE → PLAY (no gold badge promise; live hits were 0).
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

/**
 * Internal point-grade ladder → customer-safe grade.
 * STRONG PLAY / EXCEPTIONAL are never Sport Standard publish tags.
 */
export function quarantinePointGrade(
  grade: PointGrade | string | null | undefined,
): PointGrade {
  const token = String(grade ?? "PASS")
    .trim()
    .toUpperCase();
  if (token === "STRONG PLAY" || token === "EXCEPTIONAL") return "PLAY";
  if (token === "LEAN" || token === "PLAY" || token === "PASS") {
    return token;
  }
  return "PASS";
}

/** Customer surfaces never advertise Best Bet chrome. */
export function customerIsBestBet(_raw?: boolean | null): false {
  return false;
}

/**
 * Props research tags → Sport Standard publish set.
 * WATCH is legacy/internal — collapse to PASS (props board already nulls tags live).
 */
export function displayPropTag(
  tag: "PLAY" | "WATCH" | "LEAN" | "PASS" | null | undefined,
): "PLAY" | "LEAN" | "PASS" | null {
  if (tag == null) return null;
  if (tag === "WATCH") return "PASS";
  if (tag === "PLAY" && !PROP_PLAY_TIER_REACHABLE) return "PASS";
  return tag;
}

/** Prop tag filter chrome — Sport Standard only (no WATCH). */
export function reachablePropTagFilters(): readonly (
  | "PASS"
  | "LEAN"
  | "PLAY"
)[] {
  if (PROP_PLAY_TIER_REACHABLE) {
    return ["PLAY", "LEAN", "PASS"] as const;
  }
  return ["LEAN", "PASS"] as const;
}

/**
 * Quarantine a decision API blob (camel or snake) before customer JSON leaves.
 * Does not mutate engine DecisionResult objects in memory.
 */
export function quarantineDecisionForCustomer<
  T extends Record<string, unknown>,
>(raw: T): T {
  const out: Record<string, unknown> = { ...raw };
  const action =
    (typeof out.action_label === "string" ? out.action_label : null) ??
    (typeof out.actionLabel === "string" ? out.actionLabel : null);
  const shown = displayActionLabel(action as ActionLabel | null);
  if (shown) {
    if ("action_label" in out) out.action_label = shown;
    if ("actionLabel" in out) out.actionLabel = shown;
  }
  if ("point_grade" in out) {
    out.point_grade = quarantinePointGrade(
      out.point_grade as string | null | undefined,
    );
  }
  if ("pointGrade" in out) {
    out.pointGrade = quarantinePointGrade(
      out.pointGrade as string | null | undefined,
    );
  }
  if ("cover_grade" in out && out.cover_grade != null) {
    out.cover_grade = quarantinePointGrade(
      out.cover_grade as string | null | undefined,
    );
  }
  if ("coverGrade" in out && out.coverGrade != null) {
    out.coverGrade = quarantinePointGrade(
      out.coverGrade as string | null | undefined,
    );
  }
  if ("is_best_bet" in out) out.is_best_bet = false;
  if ("isBestBet" in out) out.isBestBet = false;
  return out as T;
}

export const DEAD_TIER_OPS_BLURB =
  "Hidden tiers: prop PLAY (PLAY_STAKE_ELIGIBLE=false); prop WATCH quarantined; game BEST VALUE / HIGH (tier base 0.72 < HIGH cut 0.75); ALERT/STAY AWAY/STRONG PLAY/EXCEPTIONAL/isBestBet not publish tags. Re-enable only as a product decision — not from display PRs.";
