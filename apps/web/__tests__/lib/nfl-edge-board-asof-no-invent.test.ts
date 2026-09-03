import { describe, expect, it } from "vitest";

import {
  fairLinesToEdgeBoardRows,
  resolveEdgeBoardLinesAsOf,
} from "@/lib/nfl-edge-board-from-fair-lines";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import {
  marketAsOfHeaderSuffix,
  marketAsOfStamp,
} from "@/lib/market-asof-stamp";

function fairLine(partial: Partial<NflFairLineRow> = {}): NflFairLineRow {
  return {
    gameId: "2026-W01-NE@SEA",
    season: 2026,
    week: 1,
    seasonType: "REG",
    startTime: "2026-09-10T00:20:00.000Z",
    gameDate: "2026-09-09",
    homeTeam: "Seattle Seahawks",
    awayTeam: "New England Patriots",
    homeAbbr: "SEA",
    awayAbbr: "NE",
    homeWinProb: 0.58,
    awayWinProb: 0.42,
    spreadHome: -3.9,
    totalMean: 43.4,
    fairHomeMl: -160,
    fairAwayMl: 140,
    handicapSpreadHome: -3.9,
    handicapTotal: 43.4,
    handicapHomeWinProb: 0.58,
    handicapAwayWinProb: 0.42,
    handicapHomeMl: -160,
    handicapAwayMl: 140,
    modelSpreadHome: -3.9,
    modelTotal: 43.4,
    modelHomeWinProb: 0.58,
    modelAwayWinProb: 0.42,
    modelHomeMl: -160,
    modelAwayMl: 140,
    modelEqualsKei: true,
    keiReprice: null,
    modelVersion: "test",
    simulationCount: null,
    projectionCreatedAt: null,
    marketHomeMl: null,
    marketAwayMl: null,
    marketTotal: 44.5,
    marketSpreadHome: -3.5,
    openSpreadHome: -3.0,
    openTotal: 43.0,
    oddsCapturedAt: null,
    bestSpreadHome: -3.5,
    bestTotal: 44.5,
    bestSpreadBook: "fanduel",
    bestTotalBook: "fanduel",
    bestSpreadAwayJuice: null,
    bestSpreadHomeJuice: null,
    bestTotalOverJuice: null,
    bestTotalUnderJuice: null,
    dkSpreadHome: null,
    fdSpreadHome: null,
    stakeSpreadHome: null,
    stakeSpreadBook: null,
    dkTotal: null,
    fdTotal: null,
    stakeTotal: null,
    stakeTotalBook: null,
    marketHomeProbNoVig: null,
    mlEdgeProb: null,
    totalEdge: null,
    spreadEdge: null,
    marketJoined: true,
    publishTagSpread: null,
    publishTagTotal: null,
    publishTagMl: null,
    decision: null,
    actionLabelSpread: null,
    actionLabelTotal: null,
    ...partial,
  };
}

describe("Edge Board market as-of — no invent now()", () => {
  const requestClock = "2026-09-03T01:29:52.841551+00:00";

  it("blank oddsCapturedAt → unavailable (boardAsOf request clock ignored)", () => {
    expect(
      resolveEdgeBoardLinesAsOf({
        oddsCapturedAt: null,
        boardAsOf: requestClock,
      }),
    ).toBeUndefined();

    const rows = fairLinesToEdgeBoardRows(
      [fairLine({ oddsCapturedAt: null })],
      {
        boardAsOf: requestClock,
      },
    );
    expect(rows.length).toBeGreaterThan(0);
    for (const r of rows) {
      expect((r as { linesAsOf?: string }).linesAsOf).toBeUndefined();
    }

    const header = marketAsOfHeaderSuffix({ asOf: null, kind: "lines" });
    expect(header).toBe("as-of unavailable");
    expect(header).not.toMatch(/\d{4}/);

    const stamp = marketAsOfStamp({ asOf: null, kind: "lines" });
    expect(stamp.text).toBe("Market as-of unavailable");
  });

  it("real last_update stamps; request clock never wins", () => {
    const market = "2026-09-02T18:00:00Z";
    expect(
      resolveEdgeBoardLinesAsOf({
        oddsCapturedAt: market,
        boardAsOf: requestClock,
      }),
    ).toBe(market);

    const rows = fairLinesToEdgeBoardRows(
      [fairLine({ oddsCapturedAt: market })],
      { boardAsOf: requestClock },
    );
    for (const r of rows) {
      expect((r as { linesAsOf?: string }).linesAsOf).toBe(market);
      expect((r as { linesAsOf?: string }).linesAsOf).not.toBe(requestClock);
    }
  });

  it("near-now microsecond invent on oddsCapturedAt → unavailable", () => {
    expect(
      resolveEdgeBoardLinesAsOf({
        oddsCapturedAt: requestClock,
        boardAsOf: null,
      }),
    ).toBeUndefined();
  });
});
