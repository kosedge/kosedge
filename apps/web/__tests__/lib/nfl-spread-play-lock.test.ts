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
import {
  displayActionLabel,
  NFL_PROPS_PLAY_STAKE_ELIGIBLE,
} from "@/lib/nfl-dead-tiers";
import {
  publishTagFromActionLabel,
  SPREAD_PLAY_MAX,
  SPREAD_PLAY_MIN,
  TOTAL_PLAY_ENABLED,
} from "@/lib/nfl-publish-policy";

describe("spread_play_v2_cap7 lock (Ryan 2026-09-03)", () => {
  const healthy = () => assessConfidence({ baseScore: 0.72 });

  it("ARI@LAC shape: |edge| 2.19 is never PLAY (under 2.5 floor)", () => {
    // Market LAC -10, fair ≈ -7.81 → |edge| 2.19. Cover-prob must not mint PLAY.
    const out = decideSide({
      fairSpreadHome: -7.81,
      marketSpreadHome: -10,
      week: 1,
      coverProb: 0.55,
      confidence: healthy(),
      priceStillAvailable: true,
    });
    expect(out.edgeMagnitude).toBeCloseTo(2.19, 2);
    expect(out.actionLabel).not.toBe("PLAY");
    expect(out.actionLabel).not.toBe("BEST VALUE");
    expect(out.actionLabel).toBe("LEAN");
    const shown = displayActionLabel(out.actionLabel);
    expect(shown).toBe("LEAN");
    expect(publishTagFromActionLabel(out.actionLabel)).toBe("LEAN");
    expect(publishTagFromActionLabel(out.actionLabel)).toBe(shown);
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
    expect(publishTagFromActionLabel(out.actionLabel)).toBe("PLAY");
    expect(publishTagFromActionLabel(out.actionLabel)).toBe(shown);
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
    expect(out.actionLabel).toBe("PASS");
    expect(out.reason).toContain("outside_spread_play_v2_cap7");
    const shown = displayActionLabel(out.actionLabel);
    expect(publishTagFromActionLabel(out.actionLabel)).toBe("PASS");
    expect(publishTagFromActionLabel(out.actionLabel)).toBe(shown);
  });

  it("publishTagSpread === actionLabelSpread after remap on band cases", () => {
    const cases = [
      { fair: -7.81, market: -10, week: 1 as const },
      { fair: -6.5, market: -4, week: 1 as const },
      { fair: -10, market: -3, week: 8 as const },
    ];
    for (const c of cases) {
      const out = decideSide({
        fairSpreadHome: c.fair,
        marketSpreadHome: c.market,
        week: c.week,
        confidence: healthy(),
        priceStillAvailable: true,
      });
      const shown = displayActionLabel(out.actionLabel);
      const publish = publishTagFromActionLabel(out.actionLabel);
      expect(shown === "PLAY" || shown === "LEAN" || shown === "PASS").toBe(
        true,
      );
      expect(publish).toBe(shown);
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
    expect(publishTagFromActionLabel(out.actionLabel)).not.toBe("PLAY");
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
    expect(out.modelConfidence.unresolvedFlags).toContain("conflicting_inputs");
  });
});
