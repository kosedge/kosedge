/**
 * Ryan Kos lock 2026-09-03 — spread_play_v2_cap7 + action/publish SoT.
 * Doctrine: /NFL_SPREAD_PLAY_LOCKED.md
 */
import { describe, expect, it } from "vitest";
import {
  assessConfidence,
  decideSide,
  decideTotal,
} from "@/lib/nfl-decision-engine";
import { displayActionLabel } from "@/lib/nfl-dead-tiers";
import { NFL_PROPS_PLAY_STAKE_ELIGIBLE } from "@/lib/nfl-dead-tiers";
import {
  publishTagFromActionLabel,
  SPREAD_PLAY_MAX,
  SPREAD_PLAY_MIN,
  TOTAL_PLAY_ENABLED,
} from "@/lib/nfl-publish-policy";

function sotPublish(actionLabel: ReturnType<typeof decideSide>["actionLabel"]) {
  return publishTagFromActionLabel(actionLabel);
}

describe("spread_play_v2_cap7 lock (Ryan 2026-09-03)", () => {
  const healthy = () => assessConfidence({ baseScore: 0.72 });

  it("ARI@LAC shape: |edge| 2.19 is never PLAY (under 2.5 floor)", () => {
    // Market LAC -10, fair ≈ -7.81 → |edge| 2.19. Cover-prob / key-cross must not mint PLAY.
    const out = decideSide({
      fairSpreadHome: -7.81,
      marketSpreadHome: -10,
      week: 1,
      coverProb: 0.55, // would otherwise coverWins → PLAY under early playMin path
      confidence: healthy(),
      priceStillAvailable: true,
    });
    expect(out.edgeMagnitude).toBeCloseTo(2.19, 2);
    expect(out.actionLabel).not.toBe("PLAY");
    expect(out.actionLabel).not.toBe("BEST VALUE");
    expect(["LEAN", "PASS", "ALERT", "STAY AWAY"]).toContain(out.actionLabel);
    const shown = displayActionLabel(out.actionLabel);
    expect(shown).not.toBe("PLAY");
    expect(sotPublish(out.actionLabel)).toBe(
      shown === "LEAN" ? "LEAN" : shown === "PLAY" ? "PLAY" : "PASS",
    );
    if (shown === "LEAN" || shown === "PASS" || shown === "PLAY") {
      expect(sotPublish(out.actionLabel)).toBe(
        shown === "PLAY" ? "PLAY" : shown === "LEAN" ? "LEAN" : "PASS",
      );
    }
    // Strict SoT for stake vocabulary after remap:
    expect(sotPublish(out.actionLabel)).toBe(
      publishTagFromActionLabel(out.actionLabel),
    );
    if (out.actionLabel === "LEAN" || out.actionLabel === "PASS") {
      expect(sotPublish(out.actionLabel)).toBe(out.actionLabel);
    }
  });

  it("spread |edge| 2.5 with healthy confidence → PLAY allowed", () => {
    const out = decideSide({
      fairSpreadHome: -6.5,
      marketSpreadHome: -4,
      week: 1,
      confidence: healthy(),
      priceStillAvailable: true,
    });
    expect(out.edgeMagnitude).toBeCloseTo(2.5, 5);
    expect(out.edgeMagnitude).toBeGreaterThanOrEqual(SPREAD_PLAY_MIN);
    expect(out.edgeMagnitude).toBeLessThan(SPREAD_PLAY_MAX);
    expect(["PLAY", "BEST VALUE"]).toContain(out.actionLabel);
    const shown = displayActionLabel(out.actionLabel);
    expect(shown).toBe("PLAY");
    expect(sotPublish(out.actionLabel)).toBe("PLAY");
    expect(sotPublish(out.actionLabel)).toBe(shown);
  });

  it("spread |edge| 7.0 is not PLAY in cap7 band", () => {
    const out = decideSide({
      fairSpreadHome: -10,
      marketSpreadHome: -3,
      week: 8,
      confidence: healthy(),
      priceStillAvailable: true,
    });
    expect(out.edgeMagnitude).toBeCloseTo(7.0, 5);
    expect(out.actionLabel).not.toBe("PLAY");
    expect(out.actionLabel).not.toBe("BEST VALUE");
    expect(out.reason).toContain("outside_spread_play_v2_cap7");
    const shown = displayActionLabel(out.actionLabel);
    expect(shown).not.toBe("PLAY");
    if (out.actionLabel === "PASS" || out.actionLabel === "LEAN") {
      expect(sotPublish(out.actionLabel)).toBe(out.actionLabel);
    }
  });

  it("publishTagSpread === actionLabelSpread after remap on band cases", () => {
    const cases = [
      { fair: -7.81, market: -10, week: 1 }, // 2.19
      { fair: -6.5, market: -4, week: 1 }, // 2.5
      { fair: -10, market: -3, week: 8 }, // 7.0
    ] as const;
    for (const c of cases) {
      const out = decideSide({
        fairSpreadHome: c.fair,
        marketSpreadHome: c.market,
        week: c.week,
        confidence: healthy(),
        priceStillAvailable: true,
      });
      const shown = displayActionLabel(out.actionLabel);
      const publish = sotPublish(out.actionLabel);
      expect(publish).toBe(publishTagFromActionLabel(shown));
      if (shown === "PLAY" || shown === "LEAN" || shown === "PASS") {
        expect(publish).toBe(shown);
      }
    }
  });

  it("totals never PLAY while TOTAL_PLAY_ENABLED is false", () => {
    expect(TOTAL_PLAY_ENABLED).toBe(false);
    const out = decideTotal({
      fairTotal: 47.2,
      marketTotal: 44.0,
      week: 8,
      confidence: assessConfidence({ baseScore: 0.8 }),
      priceStillAvailable: true,
    });
    expect(out.actionLabel).not.toBe("PLAY");
    expect(out.actionLabel).not.toBe("BEST VALUE");
    expect(out.reason).toContain("totals_play_sat");
    expect(sotPublish(out.actionLabel)).not.toBe("PLAY");
  });

  it("prop PLAY stake gate remains unreachable", () => {
    expect(NFL_PROPS_PLAY_STAKE_ELIGIBLE).toBe(false);
  });

  it("keeps STAY AWAY on conflicting_inputs (GB@MIN shape)", () => {
    const out = decideSide({
      fairSpreadHome: -3.5,
      marketSpreadHome: -1.09,
      week: 1,
      confidence: assessConfidence({
        baseScore: 0.72,
        conflictingInputs: true,
      }),
      priceStillAvailable: true,
    });
    expect(out.edgeMagnitude).toBeCloseTo(2.41, 2);
    expect(out.actionLabel).toBe("STAY AWAY");
    expect(out.modelConfidence.score).toBeLessThan(0.55);
  });
});
