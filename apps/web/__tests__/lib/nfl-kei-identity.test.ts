import { describe, expect, it } from "vitest";
import { keiGamesFromNflFairLines } from "@/lib/resolve-kei-lines";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";

function line(partial: Partial<NflFairLineRow> = {}): NflFairLineRow {
  return {
    gameId: "g1",
    season: 2026,
    week: 1,
    seasonType: "REG",
    startTime: "2026-09-10T00:15:00Z",
    gameDate: "2026-09-09",
    homeTeam: "Seattle Seahawks",
    awayTeam: "New England Patriots",
    homeAbbr: "SEA",
    awayAbbr: "NE",
    homeWinProb: 0.6,
    awayWinProb: 0.4,
    spreadHome: -3.5,
    totalMean: 41.3,
    fairHomeMl: -160,
    fairAwayMl: 140,
    handicapSpreadHome: -3.5,
    handicapTotal: 41.3,
    handicapHomeWinProb: 0.6,
    handicapAwayWinProb: 0.4,
    handicapHomeMl: -160,
    handicapAwayMl: 140,
    modelSpreadHome: -3.5,
    modelTotal: 41.3,
    modelHomeWinProb: 0.6,
    modelAwayWinProb: 0.4,
    modelHomeMl: -160,
    modelAwayMl: 140,
    modelEqualsKei: true,
    modelVersion: "test",
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
    ...partial,
  };
}

describe("keiGamesFromNflFairLines Model vs KEI", () => {
  it("maps published fair line to KEI with model identity when no blend split", () => {
    const [game] = keiGamesFromNflFairLines([line()]);
    expect(game?.handicapSpreadHome).toBe(-3.5);
    expect(game?.handicapTotal).toBe(41.3);
    expect(game?.projSpreadHome).toBe(-3.5);
    expect(game?.projTotal).toBe(41.3);
    expect(game?.modelSpreadHome).toBe(game?.handicapSpreadHome);
    expect(game?.modelTotal).toBe(game?.handicapTotal);
  });

  it("separates Model from KEI when API provides pre-blend model fields", () => {
    const [game] = keiGamesFromNflFairLines([
      line({
        spreadHome: -2.0,
        totalMean: 46.5,
        handicapSpreadHome: -2.0,
        handicapTotal: 46.5,
        modelSpreadHome: -4.2,
        modelTotal: 43.1,
        modelEqualsKei: false,
      }),
    ]);
    expect(game?.handicapSpreadHome).toBe(-2.0);
    expect(game?.handicapTotal).toBe(46.5);
    expect(game?.projSpreadHome).toBe(-2.0);
    expect(game?.modelSpreadHome).toBe(-4.2);
    expect(game?.modelTotal).toBe(43.1);
    expect(game?.modelSpreadHome).not.toBe(game?.handicapSpreadHome);
    expect(game?.modelTotal).not.toBe(game?.handicapTotal);
  });

  it("identity-fills model from handicap when model fields are missing", () => {
    const [game] = keiGamesFromNflFairLines([
      line({
        modelSpreadHome: null,
        modelTotal: null,
        modelHomeMl: null,
        modelAwayMl: null,
        modelHomeWinProb: null,
        modelAwayWinProb: null,
        modelEqualsKei: null,
      }),
    ]);
    expect(game?.handicapSpreadHome).toBe(-3.5);
    expect(game?.modelSpreadHome).toBe(-3.5);
    expect(game?.modelTotal).toBe(41.3);
  });
});
