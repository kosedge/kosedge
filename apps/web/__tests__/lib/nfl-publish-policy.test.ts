import { describe, expect, it } from "vitest";
import {
  nflCandidateTag,
  nflMlEvPerUnit,
  nflPublishMoneylineTag,
  nflPublishTag,
} from "@/lib/nfl-publish-policy";

describe("nfl-publish-policy", () => {
  it("defaults to PASS outside productive bands", () => {
    expect(nflCandidateTag("spread", 1.5)).toBe("PASS");
    expect(nflCandidateTag("total", 3.5)).toBe("PASS");
    expect(nflCandidateTag("total", 2.0)).toBe("PASS");
  });

  it("allows spread PLAY only in cleared bands", () => {
    expect(nflCandidateTag("spread", 2.5)).toBe("PLAY");
    expect(nflCandidateTag("spread", 6.9)).toBe("PLAY");
    expect(nflCandidateTag("spread", 7.0)).toBe("PASS"); // v2 mega-edge cap
  });

  it("forces totals PASS on sides-only launch", () => {
    expect(nflCandidateTag("total", 2.7)).toBe("PASS");
    const out = nflPublishTag("total", 2.7, "GREEN");
    expect(out.tag).toBe("PASS");
    expect(out.reason).toBe("totals_sides_only_launch");
  });

  it("forces PASS when product gate is RED", () => {
    const out = nflPublishTag("spread", 4.0, "RED");
    expect(out.tag).toBe("PASS");
    expect(out.stakeEligible).toBe(false);
  });

  it("marks PLAY stake-eligible under YELLOW/GREEN product gate", () => {
    const out = nflPublishTag("spread", 3.0, "YELLOW");
    expect(out.tag).toBe("PLAY");
    expect(out.stakeEligible).toBe(true);
  });

  it("blocks season PLAY tags on preseason games", () => {
    const out = nflPublishTag("spread", 3.5, "YELLOW", "PRE");
    expect(out.tag).toBe("PASS");
    expect(out.reason).toBe("preseason_info_desk");

    const ml = nflPublishMoneylineTag({
      spreadTag: "PLAY",
      spreadStakeEligible: true,
      modelWinProb: 0.7,
      offeredAmerican: 120,
      seasonType: "PRE",
    });
    expect(ml.tag).toBe("PASS");
    expect(ml.reason).toBe("preseason_info_desk");
  });

  it("computes vig-aware ML EV", () => {
    const ev = nflMlEvPerUnit(0.55, 150);
    expect(ev).toBeCloseTo(0.375, 6);
  });

  it("ML PLAY requires spread PLAY and EV bar", () => {
    const blocked = nflPublishMoneylineTag({
      spreadTag: "PASS",
      spreadStakeEligible: false,
      modelWinProb: 0.6,
      offeredAmerican: -110,
    });
    expect(blocked.tag).toBe("PASS");
    expect(blocked.reason).toBe("spread_not_play");

    const clear = nflPublishMoneylineTag({
      spreadTag: "PLAY",
      spreadStakeEligible: true,
      modelWinProb: 0.58,
      offeredAmerican: -110,
    });
    expect(clear.tag).toBe("PLAY");
    expect(clear.stakeEligible).toBe(true);
    expect(clear.ev).toBeGreaterThanOrEqual(0.02);
  });
});
