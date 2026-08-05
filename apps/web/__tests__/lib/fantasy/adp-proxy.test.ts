import { describe, expect, it } from "vitest";
import { adpFromModelRank, valueDelta } from "@/lib/fantasy/adp-proxy";

describe("adp proxy", () => {
  it("pushes mid QBs later than model rank", () => {
    const adp = adpFromModelRank({
      modelRank: 24,
      position: "QB",
      tier: "QB1",
      playerId: "qb-test",
    });
    expect(adp).toBeGreaterThan(24);
  });

  it("parks K/DST near the end of the draft", () => {
    const adp = adpFromModelRank({
      modelRank: 5,
      position: "K",
      tier: "elite",
      playerId: "k-test",
    });
    expect(adp).toBeGreaterThanOrEqual(140);
  });

  it("marks positive value when ADP is later than model", () => {
    expect(valueDelta(20, 35)).toBe(15);
  });
});
