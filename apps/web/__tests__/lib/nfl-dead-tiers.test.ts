import { describe, expect, it } from "vitest";
import {
  BEST_VALUE_TIER_REACHABLE,
  DEAD_TIER_OPS_BLURB,
  displayActionLabel,
  EDGES_DESK_MIN_CONF_OPTIONS,
  HIGH_CONFIDENCE_BAND_REACHABLE,
  NFL_PROPS_PLAY_STAKE_ELIGIBLE,
  PROP_PLAY_TIER_REACHABLE,
  reachableActionLabels,
  reachableConfidenceBands,
  reachablePropTagFilters,
} from "@/lib/nfl-dead-tiers";
import {
  CONFIDENCE_BEST_BET_MIN,
  CONFIDENCE_TIER_BASE,
} from "@/lib/nfl-tag-policy";

describe("NFL dead-tier honesty", () => {
  it("keeps prop PLAY unreachable while stake gate is off", () => {
    expect(NFL_PROPS_PLAY_STAKE_ELIGIBLE).toBe(false);
    expect(PROP_PLAY_TIER_REACHABLE).toBe(false);
    expect(reachablePropTagFilters()).not.toContain("PLAY");
    expect(reachablePropTagFilters()).toEqual(["WATCH", "LEAN", "PASS"]);
  });

  it("hides BEST VALUE and HIGH while tier base is below the HIGH cut", () => {
    expect(CONFIDENCE_TIER_BASE).toBeLessThan(CONFIDENCE_BEST_BET_MIN);
    expect(HIGH_CONFIDENCE_BAND_REACHABLE).toBe(false);
    expect(BEST_VALUE_TIER_REACHABLE).toBe(false);
    expect(reachableActionLabels()).not.toContain("BEST VALUE");
    expect(reachableActionLabels()).toContain("PLAY");
    expect(reachableConfidenceBands()).not.toContain("HIGH");
    expect(reachableConfidenceBands()).toEqual(["LOW", "MEDIUM"]);
  });

  it("omits the 75% Edges min-confidence chip while HIGH is unreachable", () => {
    expect(EDGES_DESK_MIN_CONF_OPTIONS).toEqual([0, 0.4, 0.6]);
    expect(EDGES_DESK_MIN_CONF_OPTIONS).not.toContain(0.75);
  });

  it("remaps unreachable BEST VALUE badge to PLAY for subscriber display", () => {
    expect(displayActionLabel("BEST VALUE")).toBe("PLAY");
    expect(displayActionLabel("PLAY")).toBe("PLAY");
    expect(displayActionLabel("LEAN")).toBe("LEAN");
    expect(displayActionLabel(null)).toBeNull();
  });

  it("documents why tiers are hidden for ops", () => {
    expect(DEAD_TIER_OPS_BLURB.toLowerCase()).toContain("play_stake_eligible");
    expect(DEAD_TIER_OPS_BLURB.toLowerCase()).toContain("0.72");
    expect(DEAD_TIER_OPS_BLURB.toLowerCase()).toContain("0.75");
  });
});
