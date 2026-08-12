import { describe, expect, it } from "vitest";
import {
  ADP_QA_GAP_DEFAULT,
  ADP_QA_GAP_TE_OR_QB2,
  adpQaGapThreshold,
  resolveAdpQaFlag,
} from "@/lib/fantasy/adp-qa-flags";
import { NEUTRAL_SCHEDULE } from "@/lib/fantasy/schedule-context";

const softSchedule = {
  early: "soft" as const,
  playoff: "hard" as const,
  label: "Soft early · Tough playoffs",
  detail: "W1–6 softer than W14–17",
};

function baseInput(
  overrides: Partial<Parameters<typeof resolveAdpQaFlag>[0]> = {},
): Parameters<typeof resolveAdpQaFlag>[0] {
  return {
    position: "WR",
    rankPosition: 24,
    rankOverall: 50,
    tier: "WR3",
    team: "KC",
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 900,
    receptionsTotal: 70,
    valueOverReplacement: 40,
    adp: 90,
    valueDelta: 40,
    existingDrivers: ["900 receiving yards (~53/g)"],
    riskFlags: [],
    schedule: NEUTRAL_SCHEDULE,
    source: "preseason-fallback",
    ...overrides,
  };
}

describe("adp-qa-flags", () => {
  it("uses 40 default and 60 for TE / QB2", () => {
    expect(adpQaGapThreshold("WR", 10)).toBe(ADP_QA_GAP_DEFAULT);
    expect(adpQaGapThreshold("RB", 8)).toBe(ADP_QA_GAP_DEFAULT);
    expect(adpQaGapThreshold("QB", 1)).toBe(ADP_QA_GAP_DEFAULT);
    expect(adpQaGapThreshold("TE", 8)).toBe(ADP_QA_GAP_TE_OR_QB2);
    expect(adpQaGapThreshold("QB", 13)).toBe(ADP_QA_GAP_TE_OR_QB2);
  });

  it("does not flag unmatched ADP", () => {
    expect(
      resolveAdpQaFlag(baseInput({ adp: null, valueDelta: null })),
    ).toBeNull();
  });

  it("does not flag a fair / modest gap", () => {
    expect(
      resolveAdpQaFlag(baseInput({ rankOverall: 12, adp: 18, valueDelta: 6 })),
    ).toBeNull();
  });

  it("does not flag TE at |Δ| 50 (below TE threshold 60)", () => {
    expect(
      resolveAdpQaFlag(
        baseInput({
          position: "TE",
          rankPosition: 8,
          rankOverall: 80,
          adp: 130,
          valueDelta: 50,
        }),
      ),
    ).toBeNull();
  });

  it("flags Gesicki-class TE gap with drivers, not lottery TD copy", () => {
    const flag = resolveAdpQaFlag(
      baseInput({
        position: "TE",
        rankPosition: 8,
        rankOverall: 47,
        tier: "TE2",
        team: "CIN",
        receivingYardsTotal: 620,
        receptionsTotal: 55,
        valueOverReplacement: 50,
        adp: 251,
        valueDelta: 204,
        existingDrivers: ["620 receiving yards (~36/g)"],
        schedule: softSchedule,
        source: "preseason-fallback",
      }),
    );
    expect(flag).not.toBeNull();
    expect(flag!.kind).toBe("model_ahead");
    expect(flag!.label).toBe("Model ≫ market");
    expect(flag!.categoryLabel).toBe("High deviation");
    expect(flag!.absGap).toBe(204);
    expect(flag!.threshold).toBe(60);
    expect(flag!.preseason).toBe(true);
    expect(flag!.drivers.length).toBeGreaterThanOrEqual(3);
    expect(flag!.drivers.join(" ")).toMatch(/CIN TE8/);
    expect(flag!.drivers.join(" ")).toMatch(/620 receiving yards/);
    expect(flag!.drivers.join(" ")).toMatch(/Value Δ \+204/);
    expect(flag!.drivers.join(" ")).toMatch(/VOR \+50/);
    expect(flag!.drivers.join(" ")).toMatch(/Preseason sim/);
    expect(flag!.drivers.join(" ")).not.toMatch(/7\.7|lottery/i);
  });

  it("flags Market ≫ model when ADP is far ahead of rank", () => {
    const flag = resolveAdpQaFlag(
      baseInput({
        position: "RB",
        rankPosition: 12,
        rankOverall: 72,
        tier: "RB2",
        team: "CHI",
        rushYardsTotal: 700,
        adp: 22,
        valueDelta: -50,
        existingDrivers: ["700 rush yards — feature-back volume on CHI"],
      }),
    );
    expect(flag?.kind).toBe("market_ahead");
    expect(flag?.label).toBe("Market ≫ model");
    expect(flag?.drivers.join(" ")).toMatch(/Value Δ -50/);
  });

  it("includes depth / availability when risk flags exist", () => {
    const flag = resolveAdpQaFlag(
      baseInput({
        valueDelta: 45,
        adp: 95,
        riskFlags: [
          {
            kind: "depth_volatility",
            label: "Depth chart",
            detail: "Listed depth 2 — role can swing with camp reshuffles.",
          },
          {
            kind: "availability",
            label: "Availability",
            detail: "Only 12 games projected — thinner than a full slate.",
          },
        ],
      }),
    );
    expect(flag?.drivers.join(" ")).toMatch(/Depth chart/);
    expect(flag?.drivers.join(" ")).toMatch(/Availability/);
  });
});
