import { describe, expect, it } from "vitest";
import { loadEdgeBoardFallback } from "@/lib/edge-board-fallback";

describe("loadEdgeBoardFallback", () => {
  it("loads shipped CFB snapshot rows", () => {
    const rows = loadEdgeBoardFallback("cfb");
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.some((r) => r.market === "Spread")).toBe(true);
    expect(rows.some((r) => r.market === "Total")).toBe(true);
  });

  it("loads shipped NHL, MLB, and WNBA snapshots", () => {
    expect(loadEdgeBoardFallback("nhl").length).toBeGreaterThan(0);
    expect(loadEdgeBoardFallback("mlb").length).toBeGreaterThan(0);
    expect(loadEdgeBoardFallback("wnba").length).toBeGreaterThan(0);
  });

  it("loads NCAAM KEI skeleton fallback (no invented book prices)", () => {
    const rows = loadEdgeBoardFallback("ncaam");
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.some((r) => r.market === "Spread")).toBe(true);
    expect(rows.every((r) => !r.best && !r.open)).toBe(true);
  });

  it("returns empty for sports without snapshot rows", () => {
    // NBA offseason: shipped file may exist with eventCount 0 / rows [].
    expect(loadEdgeBoardFallback("nba")).toEqual([]);
    expect(loadEdgeBoardFallback("not-a-sport")).toEqual([]);
  });
});

