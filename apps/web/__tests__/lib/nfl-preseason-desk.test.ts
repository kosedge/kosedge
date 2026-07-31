import { describe, expect, it } from "vitest";
import {
  campReferenceContextNote,
  campReferenceSpreadHome,
  loadPreseasonStrengthMap,
  normalizeNflAbbr,
} from "@/lib/nfl-preseason-desk";

describe("nfl-preseason-desk", () => {
  it("normalizes schedule aliases onto Kos Edge codes", () => {
    expect(normalizeNflAbbr("LA")).toBe("LAR");
    expect(normalizeNflAbbr("wsh")).toBe("WAS");
    expect(normalizeNflAbbr("JAC")).toBe("JAX");
  });

  it("loads expected-wins strength map from the latest 2026 bundle", () => {
    const map = loadPreseasonStrengthMap();
    expect(map).not.toBeNull();
    expect(map!.byTeam.size).toBe(32);
    expect(map!.leagueMeanWins).toBeGreaterThan(7);
    expect(map!.leagueMeanWins).toBeLessThan(10);
  });

  it("favors the stronger home team with reduced PRE home-field", () => {
    const map = loadPreseasonStrengthMap();
    expect(map).not.toBeNull();
    // SEA is near the top of the bundle; ARI near the bottom.
    const spread = campReferenceSpreadHome("SEA", "ARI", map);
    expect(spread).not.toBeNull();
    expect(spread!).toBeLessThan(-3);
  });

  it("returns honest PRE context copy", () => {
    expect(
      campReferenceContextNote({ hasMarket: true, hasCampRef: true }),
    ).toMatch(/not a PRE-game sim/i);
    expect(
      campReferenceContextNote({ hasMarket: true, hasCampRef: false }),
    ).toMatch(/market board only/i);
  });
});
