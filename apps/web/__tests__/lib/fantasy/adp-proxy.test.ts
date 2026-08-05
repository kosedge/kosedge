import { describe, expect, it } from "vitest";
import {
  adpFromModelRank,
  formatAdp,
  valueDelta,
  valueLabel,
} from "@/lib/fantasy/adp-proxy";

describe("adp helpers", () => {
  it("legacy proxy still pushes mid QBs later than model rank", () => {
    const adp = adpFromModelRank({
      modelRank: 24,
      position: "QB",
      tier: "QB1",
      playerId: "qb-test",
    });
    expect(adp).toBeGreaterThan(24);
  });

  it("marks positive value when ADP is later than model", () => {
    expect(valueDelta(20, 35)).toBe(15);
  });

  it("formats missing ADP honestly", () => {
    expect(formatAdp(null)).toBe("—");
    expect(valueLabel(null).kind).toBe("na");
    expect(valueLabel(12).kind).toBe("value");
  });
});
