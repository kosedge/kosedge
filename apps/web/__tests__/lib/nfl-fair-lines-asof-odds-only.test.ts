import { describe, expect, it } from "vitest";

import {
  marketAsOfHeaderSuffix,
  marketAsOfStamp,
  sanitizeMarketCaptureIso,
} from "@/lib/market-asof-stamp";

/**
 * Fair-lines must stamp model odds_as_of (e.g. Aug 21), never render/request time.
 * Mirrors apps/web/app/(pro)/pro/nfl/fair-lines/page.tsx:
 *   const marketAsOf = board.oddsAsOf?.trim() || null;
 */
function fairLinesMarketAsOf(board: {
  oddsAsOf: string | null;
  asOf?: string | null;
  lines?: Array<{ oddsCapturedAt: string | null }>;
}): string | null {
  // Contract: oddsAsOf only — ignore board.asOf and row clocks.
  void board.asOf;
  void board.lines;
  return board.oddsAsOf?.trim() || null;
}

describe("fair-lines as-of = model odds_as_of", () => {
  const storedOddsAsOf = "2026-08-21T13:42:55+00:00";
  const requestInvent = "2026-09-03T01:36:14.123456+00:00";
  const renderDay = "2026-09-02T18:00:00.000Z";

  it("equals stored odds_as_of when present (not Sep 2 render / invent)", () => {
    const marketAsOf = fairLinesMarketAsOf({
      oddsAsOf: storedOddsAsOf,
      asOf: requestInvent,
      lines: [{ oddsCapturedAt: renderDay }],
    });
    expect(marketAsOf).toBe(storedOddsAsOf);
    expect(marketAsOf).not.toBe(requestInvent);
    expect(marketAsOf).not.toBe(renderDay);

    const header = marketAsOfHeaderSuffix({
      asOf: marketAsOf,
      kind: "lines",
      nowMs: Date.parse("2026-09-03T01:36:20.000Z"),
    });
    expect(header).toMatch(/^as of /);
    expect(header).toMatch(/Aug/);
    expect(header).toContain("stale");
    expect(header).not.toMatch(/Sep 2/);
  });

  it("unavailable when odds_as_of blank — never Date.now() / asOf invent", () => {
    const marketAsOf = fairLinesMarketAsOf({
      oddsAsOf: null,
      asOf: requestInvent,
      lines: [{ oddsCapturedAt: renderDay }],
    });
    expect(marketAsOf).toBeNull();
    expect(sanitizeMarketCaptureIso(requestInvent)).toBeNull();
    expect(marketAsOfStamp({ asOf: marketAsOf, kind: "lines" }).text).toBe(
      "Market as-of unavailable",
    );
    expect(marketAsOfHeaderSuffix({ asOf: marketAsOf, kind: "lines" })).toBe(
      "as-of unavailable",
    );
  });
});
