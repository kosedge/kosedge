import { describe, expect, it } from "vitest";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import {
  buildNflPickemCard,
  filterPickemWeekLines,
  resolvePickemTag,
} from "@/lib/nfl-pickem";

function line(partial: Partial<NflFairLineRow>): NflFairLineRow {
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
    keiReprice: null,
    modelVersion: "test",
    simulationCount: 1000,
    projectionCreatedAt: null,
    marketHomeMl: null,
    marketAwayMl: null,
    marketTotal: 44.5,
    marketSpreadHome: -3.0,
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
    marketJoined: true,
    publishTagSpread: "PASS",
    publishTagTotal: "PASS",
    publishTagMl: "PASS",
    decision: null,
    actionLabelSpread: null,
    actionLabelTotal: null,
    ...partial,
  };
}

function makeSlate(n: number): NflFairLineRow[] {
  return Array.from({ length: n }, (_, i) => {
    const homeWin = 0.52 + i * 0.01;
    return line({
      gameId: `g${String(i + 1).padStart(2, "0")}`,
      homeAbbr: `H${i}`,
      awayAbbr: `A${i}`,
      homeTeam: `Home ${i}`,
      awayTeam: `Away ${i}`,
      handicapHomeWinProb: homeWin,
      handicapAwayWinProb: 1 - homeWin,
      homeWinProb: homeWin,
      awayWinProb: 1 - homeWin,
      handicapSpreadHome: -(i + 1),
      spreadHome: -(i + 1),
      startTime: `2026-09-14T${String(17 + (i % 6)).padStart(2, "0")}:00:00Z`,
      publishTagSpread: "PASS",
      publishTagMl: "PASS",
    });
  });
}

describe("buildNflPickemCard", () => {
  it("assigns unique ranks N..1 for a 16-game slate", () => {
    const card = buildNflPickemCard(makeSlate(16));
    expect(card).toHaveLength(16);
    const confidences = card.map((p) => p.confidence);
    expect(confidences).toEqual([16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]);
    expect(new Set(confidences).size).toBe(16);
  });

  it("sorts PLAY above LEAN above PASS, then by win-prob gap", () => {
    const lines = [
      line({
        gameId: "pass-big",
        publishTagSpread: "PASS",
        handicapHomeWinProb: 0.75,
        handicapAwayWinProb: 0.25,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "lean-mid",
        publishTagSpread: "LEAN",
        handicapHomeWinProb: 0.6,
        handicapAwayWinProb: 0.4,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "play-small",
        publishTagSpread: "PLAY",
        handicapHomeWinProb: 0.55,
        handicapAwayWinProb: 0.45,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "play-big",
        publishTagMl: "PLAY",
        publishTagSpread: "PASS",
        handicapHomeWinProb: 0.7,
        handicapAwayWinProb: 0.3,
        startTime: "2026-09-14T20:00:00Z",
      }),
    ];
    const card = buildNflPickemCard(lines);
    expect(card.map((p) => p.gameId)).toEqual([
      "play-big",
      "play-small",
      "lean-mid",
      "pass-big",
    ]);
    expect(card.map((p) => p.confidence)).toEqual([4, 3, 2, 1]);
    expect(card[0]!.tag).toBe("PLAY");
    expect(card[2]!.tag).toBe("LEAN");
  });

  it("picks the KEI win-prob side (SU), not ATS from spread PLAY", () => {
    const card = buildNflPickemCard([
      line({
        gameId: "away-fav",
        handicapHomeWinProb: 0.4,
        handicapAwayWinProb: 0.6,
        handicapSpreadHome: 3.5,
        publishTagSpread: "PLAY",
      }),
    ]);
    expect(card[0]!.side).toBe("away");
    expect(card[0]!.pickAbbr).toBe("NE");
    expect(card[0]!.oppAbbr).toBe("SEA");
    expect(card[0]!.winProb).toBe(0.6);
    expect(card[0]!.keiSpreadPick).toBe(-3.5);
    expect(card[0]!.tag).toBe("PLAY");
  });

  it("sinks missing win probs to the bottom with side null", () => {
    const lines = [
      line({
        gameId: "no-prob",
        handicapHomeWinProb: null,
        handicapAwayWinProb: null,
        homeWinProb: null,
        awayWinProb: null,
        publishTagSpread: "PLAY",
        startTime: "2026-09-14T13:00:00Z",
      }),
      line({
        gameId: "has-prob",
        handicapHomeWinProb: 0.55,
        handicapAwayWinProb: 0.45,
        publishTagSpread: "PASS",
        startTime: "2026-09-14T20:00:00Z",
      }),
    ];
    const card = buildNflPickemCard(lines);
    expect(card[0]!.gameId).toBe("has-prob");
    expect(card[0]!.confidence).toBe(2);
    expect(card[1]!.gameId).toBe("no-prob");
    expect(card[1]!.side).toBe(null);
    expect(card[1]!.pickAbbr).toBe(null);
    expect(card[1]!.winProb).toBe(null);
    expect(card[1]!.confidence).toBe(1);
  });

  it("falls back to |KEI spread| when win-prob gap ties and never invents", () => {
    const lines = [
      line({
        gameId: "narrow",
        handicapHomeWinProb: 0.6,
        handicapAwayWinProb: 0.4,
        handicapSpreadHome: -2,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "wide",
        handicapHomeWinProb: 0.6,
        handicapAwayWinProb: 0.4,
        handicapSpreadHome: -7,
        startTime: "2026-09-14T17:00:00Z",
      }),
    ];
    const card = buildNflPickemCard(lines);
    // Same gap (0.1); larger |spread| first.
    expect(card.map((p) => p.gameId)).toEqual(["wide", "narrow"]);
  });

  it("tie-breaks by earlier kickoff then gameId", () => {
    const lines = [
      line({
        gameId: "b",
        handicapHomeWinProb: 0.6,
        handicapAwayWinProb: 0.4,
        handicapSpreadHome: -3,
        startTime: "2026-09-14T20:00:00Z",
      }),
      line({
        gameId: "a",
        handicapHomeWinProb: 0.6,
        handicapAwayWinProb: 0.4,
        handicapSpreadHome: -3,
        startTime: "2026-09-14T17:00:00Z",
      }),
    ];
    const card = buildNflPickemCard(lines);
    expect(card.map((p) => p.gameId)).toEqual(["a", "b"]);
  });

  it("uses ML PLAY tag for bucket when spread is PASS", () => {
    expect(
      resolvePickemTag(
        line({ publishTagSpread: "PASS", publishTagMl: "PLAY" }),
      ),
    ).toBe("PLAY");
  });

  it("shrinks N with bye weeks (fewer games)", () => {
    const card = buildNflPickemCard(makeSlate(14));
    expect(card.map((p) => p.confidence)).toEqual([
      14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
    ]);
  });
});

describe("filterPickemWeekLines", () => {
  it("keeps REG for the requested week and drops PRE", () => {
    const lines = [
      line({ gameId: "reg1", week: 1, seasonType: "REG" }),
      line({ gameId: "pre1", week: 1, seasonType: "PRE" }),
      line({ gameId: "reg2", week: 2, seasonType: "REG" }),
    ];
    const week1 = filterPickemWeekLines(lines, 1);
    expect(week1.map((r) => r.gameId)).toEqual(["reg1"]);
  });
});
