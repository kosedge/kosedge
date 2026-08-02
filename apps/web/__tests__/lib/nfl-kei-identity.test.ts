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
    modelVersion: "test",
    simulationCount: 1000,
    projectionCreatedAt: null,
    marketHomeMl: null,
    marketAwayMl: null,
    marketTotal: null,
    marketSpreadHome: null,
    bestSpreadHome: null,
    bestTotal: null,
    bestSpreadBook: null,
    bestTotalBook: null,
    bestSpreadAwayJuice: null,
    bestSpreadHomeJuice: null,
    bestTotalOverJuice: null,
    bestTotalUnderJuice: null,
    marketHomeProbNoVig: null,
    mlEdgeProb: null,
    totalEdge: null,
    spreadEdge: null,
    marketJoined: false,
    publishTagSpread: "PASS",
    publishTagTotal: "PASS",
    publishTagMl: "PASS",
    ...partial,
  };
}

describe("keiGamesFromNflFairLines honesty", () => {
  it("maps published fair line to KEI with model identity (no fake split)", () => {
    const [game] = keiGamesFromNflFairLines([line()]);
    expect(game?.handicapSpreadHome).toBe(-3.5);
    expect(game?.handicapTotal).toBe(41.3);
    expect(game?.projSpreadHome).toBe(-3.5);
    expect(game?.projTotal).toBe(41.3);
    // Identity: model mirrors handicap until a real pre_blend/model feed exists.
    expect(game?.modelSpreadHome).toBe(game?.handicapSpreadHome);
    expect(game?.modelTotal).toBe(game?.handicapTotal);
  });

  it("ignores untyped stub model fields on the fair-line row", () => {
    const dirty = {
      ...line(),
      modelSpreadHome: -99,
      preBlendSpreadHome: -88,
      modelTotal: 99,
      preBlendTotal: 88,
    } as NflFairLineRow & {
      modelSpreadHome: number;
      preBlendSpreadHome: number;
      modelTotal: number;
      preBlendTotal: number;
    };
    const [game] = keiGamesFromNflFairLines([dirty]);
    expect(game?.handicapSpreadHome).toBe(-3.5);
    expect(game?.modelSpreadHome).toBe(-3.5);
    expect(game?.modelTotal).toBe(41.3);
  });
});
