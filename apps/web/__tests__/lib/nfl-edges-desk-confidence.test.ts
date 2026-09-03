import { describe, expect, it } from "vitest";
import { deskEdgesFromFairLine } from "@/lib/nfl-edges";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";

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
    spreadHome: -3.87,
    totalMean: 43.4,
    fairHomeMl: -160,
    fairAwayMl: 140,
    handicapSpreadHome: -3.87,
    handicapTotal: 43.4,
    handicapHomeWinProb: 0.58,
    handicapAwayWinProb: 0.42,
    handicapHomeMl: -160,
    handicapAwayMl: 140,
    modelSpreadHome: -3.87,
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
    marketHomeMl: -150,
    marketAwayMl: 130,
    marketTotal: 48.5,
    marketSpreadHome: -3.5,
    openSpreadHome: -3.0,
    openTotal: 43.0,
    oddsCapturedAt: "2026-08-21T13:42:55+00:00",
    bestSpreadHome: -3.5,
    bestTotal: 48.5,
    bestSpreadBook: "fanduel",
    bestTotalBook: "fanduel",
    bestSpreadAwayJuice: null,
    bestSpreadHomeJuice: null,
    bestTotalOverJuice: null,
    bestTotalUnderJuice: null,
    dkSpreadHome: null,
    fdSpreadHome: -3.5,
    stakeSpreadHome: -3.5,
    stakeSpreadBook: "fanduel",
    dkTotal: null,
    fdTotal: 48.5,
    stakeTotal: 48.5,
    stakeTotalBook: "fanduel",
    marketHomeProbNoVig: null,
    mlEdgeProb: 0.03,
    totalEdge: 1.26,
    spreadEdge: 0.37,
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

describe("deskEdgesFromFairLine confidence", () => {
  it("inherits per-market decision confidence with row-level fallback", () => {
    const row = fairLine({
      spreadEdge: 0.37,
      totalEdge: 2.41,
      decision: {
        week: 1,
        weekRegime: "early",
        spread: {
          market: "spread",
          actionLabel: "PASS",
          pointGrade: "PASS",
          edgeMagnitude: 0.37,
          modelConfidence: {
            score: 0.72,
            band: "MEDIUM",
            factors: {},
            unresolvedFlags: [],
          },
          coverProb: null,
          coverGrade: null,
          playTo: null,
          marketConfirmation: {
            modelFair: null,
            opening: null,
            current: null,
            closing: null,
            confirmsThesis: null,
            weakensThesis: null,
            note: "",
          },
          isBestBet: false,
          modelWarning: false,
          keyNumberCross: false,
          priceStillAvailable: true,
          numericalEdge: true,
          confidenceOk: true,
          reason: "",
          week: 1,
          weekRegime: "early",
          fairLine: -3.87,
          marketLine: -3.5,
        },
        total: {
          market: "total",
          actionLabel: "STAY AWAY",
          pointGrade: "PASS",
          edgeMagnitude: 2.41,
          modelConfidence: {
            score: 0.47,
            band: "LOW",
            factors: {},
            unresolvedFlags: ["conflicting_inputs"],
          },
          coverProb: null,
          coverGrade: null,
          playTo: null,
          marketConfirmation: {
            modelFair: null,
            opening: null,
            current: null,
            closing: null,
            confirmsThesis: null,
            weakensThesis: null,
            note: "",
          },
          isBestBet: false,
          modelWarning: false,
          keyNumberCross: false,
          priceStillAvailable: true,
          numericalEdge: true,
          confidenceOk: false,
          reason: "",
          week: 1,
          weekRegime: "early",
          fairLine: 47.2,
          marketLine: 48.5,
        },
        edgeMagnitudeSpread: 0.37,
        edgeMagnitudeTotal: 2.41,
        modelConfidence: {
          score: 0.5,
          band: "LOW",
          factors: {},
          unresolvedFlags: [],
        },
        actionLabelSpread: "PASS",
        actionLabelTotal: "STAY AWAY",
      },
    });

    const edges = deskEdgesFromFairLine(row, {
      minProbEdge: 0.02,
      minLineEdge: 0.3,
    });
    const spread = edges.find((e) => e.marketType === "spread");
    const total = edges.find((e) => e.marketType === "total");
    expect(spread?.confidence).toBe(0.72);
    expect(total?.confidence).toBe(0.47);
  });

  it("keeps null confidence when decision is absent", () => {
    const edges = deskEdgesFromFairLine(
      fairLine({ spreadEdge: 0.71, decision: null }),
      { minProbEdge: 0.02, minLineEdge: 0.5 },
    );
    const spread = edges.find((e) => e.marketType === "spread");
    expect(spread?.confidence).toBeNull();
  });
});
