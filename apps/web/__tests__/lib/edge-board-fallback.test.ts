import { describe, expect, it } from "vitest";
import { loadEdgeBoardFallback } from "@/lib/edge-board-fallback";

describe("loadEdgeBoardFallback", () => {
  it("loads shipped CFB snapshot rows", () => {
    const rows = loadEdgeBoardFallback("cfb");
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.some((r) => r.market === "Spread")).toBe(true);
    expect(rows.some((r) => r.market === "Total")).toBe(true);
  });

  it("loads shipped NHL and MLB snapshots", () => {
    expect(loadEdgeBoardFallback("nhl").length).toBeGreaterThan(0);
    expect(loadEdgeBoardFallback("mlb").length).toBeGreaterThan(0);
  });

  it("returns empty for sports without a snapshot", () => {
    expect(loadEdgeBoardFallback("wnba")).toEqual([]);
    expect(loadEdgeBoardFallback("not-a-sport")).toEqual([]);
  });
});
