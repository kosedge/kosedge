import { describe, expect, it } from "vitest";

import {
  MARKET_ASOF_STALE_MS,
  boardAsOfFromUpdatedAts,
  formatMarketAsOfDisplay,
  marketAsOfStamp,
  pickLatestIso,
} from "@/lib/market-asof-stamp";

describe("market-asof-stamp", () => {
  it("does not fabricate a timestamp when source is blank", () => {
    for (const blank of [null, undefined, "", "   "]) {
      const stamp = marketAsOfStamp({ asOf: blank, kind: "odds" });
      expect(stamp.missing).toBe(true);
      expect(stamp.stale).toBe(false);
      expect(stamp.asOfIso).toBeNull();
      expect(stamp.text).toBe("Market as-of unavailable");
      expect(stamp.text).not.toMatch(/\d{4}/);
    }
  });

  it("stamps book + as-of when present (Compare Odds copy)", () => {
    const stamp = marketAsOfStamp({
      asOf: "2026-09-02T18:00:00.000Z",
      books: ["DraftKings", "FanDuel"],
      kind: "odds",
      nowMs: Date.parse("2026-09-02T19:00:00.000Z"),
    });
    expect(stamp.missing).toBe(false);
    expect(stamp.stale).toBe(false);
    expect(stamp.text).toContain("Odds as of");
    expect(stamp.text).toContain("DraftKings");
    expect(stamp.text).toContain("FanDuel");
    expect(stamp.text).not.toContain("unavailable");
  });

  it("marks stale when older than 6h and keeps source clock", () => {
    const asOf = "2026-09-01T12:00:00.000Z";
    const stamp = marketAsOfStamp({
      asOf,
      kind: "lines",
      nowMs: Date.parse("2026-09-02T00:00:00.000Z"),
      staleMs: MARKET_ASOF_STALE_MS,
    });
    expect(stamp.stale).toBe(true);
    expect(stamp.text).toContain("Lines as of");
    expect(stamp.text).toContain("stale");
    expect(stamp.asOfIso).toBe(asOf);
  });

  it("pickLatestIso ignores blank / invalid and never invents now", () => {
    expect(pickLatestIso(null, undefined, "", "not-a-date")).toBeNull();
    expect(
      pickLatestIso(
        "2026-08-21T13:42:55+00:00",
        "2026-09-02T15:00:00.000Z",
        null,
      ),
    ).toBe("2026-09-02T15:00:00.000Z");
  });

  it("boardAsOfFromUpdatedAts refuses editorial fallback when blank", () => {
    expect(boardAsOfFromUpdatedAts([null, undefined, ""])).toBeNull();
    expect(
      boardAsOfFromUpdatedAts([
        null,
        "2026-09-02T10:00:00.000Z",
        "2026-09-01T10:00:00.000Z",
      ]),
    ).toBe("2026-09-02T10:00:00.000Z");
  });

  it("formatMarketAsOfDisplay is stable ET label", () => {
    const label = formatMarketAsOfDisplay("2026-09-02T18:00:00.000Z");
    expect(label).toMatch(/Sep/);
    expect(label).toMatch(/2026/);
  });
});
