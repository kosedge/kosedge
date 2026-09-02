import { describe, expect, it } from "vitest";
import {
  sportHasKeiSource,
  sportIsMarketsOnlyEdgeBoard,
} from "@/lib/edge-board-kei-availability";

describe("edge-board-kei-availability", () => {
  it("marks MLB/NFL/NBA/WNBA/NCAAM/CFB/NHL as KEI-sourced", () => {
    for (const s of ["mlb", "nfl", "nba", "wnba", "ncaam", "cfb", "nhl"]) {
      expect(sportHasKeiSource(s)).toBe(true);
      expect(sportIsMarketsOnlyEdgeBoard(s)).toBe(false);
    }
  });

  it("no longer treats NHL as markets-only after Ch4", () => {
    expect(sportHasKeiSource("nhl")).toBe(true);
    expect(sportIsMarketsOnlyEdgeBoard("nhl")).toBe(false);
  });
});
