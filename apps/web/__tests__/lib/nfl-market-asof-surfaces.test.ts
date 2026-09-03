import { describe, expect, it } from "vitest";

import { marketAsOfStamp } from "@/lib/market-asof-stamp";

/**
 * Surface contracts: Compare Odds + at least one other NFL market table
 * must expose honest as-of / stale copy (never invent a clock).
 */
describe("NFL market as-of surface copy", () => {
  it("Compare Odds stamp includes Odds as of + books when source present", () => {
    const stamp = marketAsOfStamp({
      asOf: "2026-09-02T17:00:00.000Z",
      books: ["DraftKings", "FanDuel"],
      kind: "odds",
      nowMs: Date.parse("2026-09-02T18:00:00.000Z"),
    });
    expect(stamp.text).toMatch(/^Odds as of /);
    expect(stamp.text).toContain("DraftKings");
    expect(stamp.missing).toBe(false);
  });

  it("Compare Odds says unavailable when Odds API omitted last_update", () => {
    const stamp = marketAsOfStamp({ asOf: null, kind: "odds" });
    expect(stamp.text).toBe("Market as-of unavailable");
    expect(stamp.asOfIso).toBeNull();
  });

  it("KEI Lines / Edges / Edge Board share Lines|Market stamp (not invented)", () => {
    const lines = marketAsOfStamp({
      asOf: "2026-09-02T15:00:00.000Z",
      books: ["DraftKings"],
      kind: "lines",
      nowMs: Date.parse("2026-09-02T16:00:00.000Z"),
    });
    expect(lines.text).toMatch(/^Lines as of /);
    expect(lines.text).toContain("DraftKings");

    const missing = marketAsOfStamp({ asOf: "", kind: "market" });
    expect(missing.text).toBe("Market as-of unavailable");
    expect(missing.text).not.toMatch(/August 11/);
  });

  it("Props board refuses editorial date when updatedAt is blank", () => {
    const stamp = marketAsOfStamp({ asOf: null, kind: "board" });
    expect(stamp.missing).toBe(true);
    expect(stamp.text).toBe("Market as-of unavailable");
    // Former props asOfLabel fell back to KOSEDGE_DATE — must not reappear.
    expect(stamp.text).not.toContain("August 11, 2026");
  });
});
