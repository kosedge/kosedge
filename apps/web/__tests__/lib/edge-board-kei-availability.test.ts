import { describe, expect, it } from "vitest";
import {
  sportHasKeiSource,
  sportIsMarketsOnlyEdgeBoard,
} from "@/lib/edge-board-kei-availability";

describe("edge-board-kei-availability", () => {
  it("marks MLB/NFL/NBA/WNBA/NCAAM as KEI-sourced", () => {
    for (const s of ["mlb", "nfl", "nba", "wnba", "ncaam", "cfb"]) {
      expect(sportHasKeiSource(s)).toBe(true);
      expect(sportIsMarketsOnlyEdgeBoard(s)).toBe(false);
    }
  });

  it("marks NHL as markets-only; CFB has a KEI source", () => {
    expect(sportHasKeiSource("nhl")).toBe(false);
    expect(sportHasKeiSource("cfb")).toBe(true);
    expect(sportIsMarketsOnlyEdgeBoard("nhl")).toBe(true);
    expect(sportIsMarketsOnlyEdgeBoard("cfb")).toBe(false);
  });
});
