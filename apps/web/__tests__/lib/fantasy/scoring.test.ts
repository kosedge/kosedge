import { describe, expect, it } from "vitest";
import {
  fantasyPointsFromBox,
  floorMedianCeilingFromMean,
} from "@/lib/fantasy/scoring";

describe("fantasy scoring", () => {
  it("scores half-PPR receptions at 0.5", () => {
    const pts = fantasyPointsFromBox({
      scoringProfile: "half_ppr",
      receivingYards: 100,
      receptions: 10,
      recTds: 1,
    });
    expect(pts).toBeCloseTo(10 + 5 + 6, 4);
  });

  it("widens floor/ceiling for rookies", () => {
    const vet = floorMedianCeilingFromMean({
      medianPoints: 200,
      position: "RB",
    });
    const rook = floorMedianCeilingFromMean({
      medianPoints: 200,
      position: "RB",
      isRookie: true,
    });
    expect(rook.floorPoints).toBeLessThan(vet.floorPoints);
    expect(rook.ceilingPoints).toBeGreaterThan(vet.ceilingPoints);
  });
});
