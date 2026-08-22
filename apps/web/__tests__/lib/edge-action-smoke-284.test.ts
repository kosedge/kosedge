/**
 * PR #284 smoke — Edge Action vs Current coherence (no behavior rewrite).
 */
import { describe, expect, it } from "vitest";
import {
  fairLinesToEdgeBoardRows,
  overlayOddsOntoFairLineRows,
  syncEdgeBoardActionsWithCurrent,
} from "@/lib/nfl-edge-board-from-fair-lines";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";

function baseLine(
  overrides: Partial<NflFairLineRow>,
): NflFairLineRow {
  return {
    gameId: "g1",
    season: 2026,
    week: 1,
    seasonType: "REG",
    startTime: "2026-09-09T20:00:00Z",
    gameDate: "2026-09-09",
    homeTeam: "Seattle Seahawks",
    awayTeam: "New England Patriots",
    homeAbbr: "SEA",
    awayAbbr: "NE",
    homeWinProb: 0.62,
    awayWinProb: 0.38,
    spreadHome: -4.22,
    totalMean: 43.33,
    fairHomeMl: -180,
    fairAwayMl: 155,
    handicapSpreadHome: -4.22,
    handicapTotal: 43.33,
    handicapHomeWinProb: 0.62,
    handicapAwayWinProb: 0.38,
    handicapHomeMl: -180,
    handicapAwayMl: 140,
    modelSpreadHome: -4.22,
    modelTotal: 43.33,
    modelHomeWinProb: 0.62,
    modelAwayWinProb: 0.38,
    modelHomeMl: -180,
    modelAwayMl: 140,
    modelEqualsKei: true,
    modelVersion: "smoke",
    simulationCount: 1000,
    projectionCreatedAt: null,
    marketHomeMl: null,
    marketAwayMl: null,
    marketTotal: null,
    marketSpreadHome: null,
    openSpreadHome: null,
    openTotal: null,
    oddsCapturedAt: null,
    bestSpreadHome: null,
    bestTotal: null,
    bestSpreadBook: null,
    bestTotalBook: null,
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
    marketJoined: false,
    publishTagSpread: "PASS",
    publishTagTotal: "PASS",
    publishTagMl: "PASS",
    decision: null,
    actionLabelSpread: null,
    actionLabelTotal: null,
    ...overrides,
  };
}

function assemble(
  line: NflFairLineRow,
  odds: Parameters<typeof overlayOddsOntoFairLineRows>[1],
) {
  const fair = fairLinesToEdgeBoardRows([line]);
  const overlaid = overlayOddsOntoFairLineRows(fair, odds);
  return syncEdgeBoardActionsWithCurrent(overlaid);
}

describe("PR #284 smoke — Edge Action vs Current", () => {
  it("NE@SEA: Action edge 0.7 / 1.2 with Mkt −3.5 / 44.5 (not 0.0)", () => {
    const rows = assemble(baseLine({}), [
      {
        id: "ne-spread",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        best: "+3.5",
        bookKey: "fanduel",
      } as any,
      {
        id: "ne-total",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Total",
        best: "44.5",
        bookKey: "fanduel",
      } as any,
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBeUndefined();
    expect(spread.best).toBe("+3.5");
    expect((spread as any).decisionMarketLine).toBe(-3.5);
    expect((spread as any).edgeMagnitude).toBeCloseTo(0.7, 1);
    expect((spread as any).actionLabel).toBe("PASS");
    expect((total as any).decisionMarketLine).toBe(44.5);
    expect((total as any).edgeMagnitude).toBeCloseTo(1.2, 1);
    expect((spread as any).edgeMagnitude).not.toBe(0);
    expect((total as any).edgeMagnitude).not.toBe(0);
  });

  it("CLE@JAX: open present, Current grades Action (not fake 0.0)", () => {
    const rows = assemble(
      baseLine({
        gameId: "cle-jax",
        homeTeam: "Jacksonville Jaguars",
        awayTeam: "Cleveland Browns",
        homeAbbr: "JAX",
        awayAbbr: "CLE",
        spreadHome: -6.86,
        handicapSpreadHome: -6.86,
        modelSpreadHome: -6.86,
        totalMean: 41.46,
        handicapTotal: 41.46,
        modelTotal: 41.46,
        openSpreadHome: -7.5,
        openTotal: 40.5,
      }),
      [
        {
          id: "cle-spread",
          game: "Cleveland Browns @ Jacksonville Jaguars",
          market: "Spread",
          best: "+7.5",
          bookKey: "draftkings",
        } as any,
        {
          id: "cle-total",
          game: "Cleveland Browns @ Jacksonville Jaguars",
          market: "Total",
          best: "41.0",
          bookKey: "draftkings",
        } as any,
      ],
    );
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBe("+7.5");
    expect(total.open).toBe("40.5");
    expect(spread.best).toBe("+7.5");
    // Open from snapshot; Current may match when line unchanged — not invented open.
    expect((spread as any).decisionMarketLine).toBe(-7.5);
    expect((spread as any).edgeMagnitude).toBeCloseTo(0.6, 1);
    expect((spread as any).edgeMagnitude).not.toBe(0);
    expect((total as any).edgeMagnitude).toBeCloseTo(0.5, 1);
  });

  it("BUF@HOU: third W1 game with open + Current", () => {
    const rows = assemble(
      baseLine({
        gameId: "buf-hou",
        homeTeam: "Houston Texans",
        awayTeam: "Buffalo Bills",
        homeAbbr: "HOU",
        awayAbbr: "BUF",
        spreadHome: 0.68,
        handicapSpreadHome: 0.68,
        modelSpreadHome: 0.68,
        totalMean: 43.8,
        handicapTotal: 43.8,
        modelTotal: 43.8,
        openSpreadHome: 1.5,
        openTotal: 44.5,
      }),
      [
        {
          id: "buf-spread",
          game: "Buffalo Bills @ Houston Texans",
          market: "Spread",
          best: "+1.5",
          bookKey: "fanduel",
        } as any,
        {
          id: "buf-total",
          game: "Buffalo Bills @ Houston Texans",
          market: "Total",
          best: "44.0",
          bookKey: "fanduel",
        } as any,
      ],
    );
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBe("-1.5");
    expect((spread as any).decisionMarketLine).toBe(-1.5);
    expect((spread as any).edgeMagnitude).not.toBe(0);
    expect((total as any).decisionMarketLine).toBe(44);
    expect((total as any).edgeMagnitude).not.toBe(0);
  });

  it("DAL@NYG: missing open stays —; never open = current", () => {
    const rows = assemble(
      baseLine({
        gameId: "dal-nyg",
        homeTeam: "New York Giants",
        awayTeam: "Dallas Cowboys",
        homeAbbr: "NYG",
        awayAbbr: "DAL",
        spreadHome: 1.88,
        handicapSpreadHome: 1.88,
        totalMean: 47.24,
        handicapTotal: 47.24,
      }),
      [
        {
          id: "dal-spread",
          game: "Dallas Cowboys @ New York Giants",
          market: "Spread",
          best: "+2.5",
          bookKey: "fanduel",
        } as any,
        {
          id: "dal-total",
          game: "Dallas Cowboys @ New York Giants",
          market: "Total",
          best: "46.5",
          bookKey: "fanduel",
        } as any,
      ],
    );
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBeUndefined();
    expect(total.open).toBeUndefined();
    expect(spread.best).toBe("+2.5");
    expect((spread as any).edgeMagnitude).not.toBe(0);
    expect(spread.open).not.toBe(spread.best);
  });
});
