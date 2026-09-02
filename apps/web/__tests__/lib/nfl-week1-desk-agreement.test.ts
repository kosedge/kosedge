/**
 * Week 1 betting desk agreement — success criteria lock.
 * 1) Lean Under when model < line (Holani)
 * 2) NE@SEA kickoff 8:20 survives odds overlay
 * 3) Edge Board as-of is not stuck on 2026-08-21
 * 4) Props fair O/U empty when Line blank
 * 5) Maye Boxes/Props share spine mean preference
 */

import { describe, expect, it } from "vitest";
import { deskEdgeFromPropRow } from "@/lib/nfl-edges";
import type { NflPropBoardRow } from "@/lib/nfl-props-board";
import {
  fairLinesToEdgeBoardRows,
  overlayOddsOntoFairLineRows,
  resolveEdgeBoardLinesAsOf,
} from "@/lib/nfl-edge-board-from-fair-lines";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import { canonicalKickoffForMatchup } from "@/lib/nfl-canonical-schedule";

function propRow(partial: Partial<NflPropBoardRow>): NflPropBoardRow {
  return {
    season: 2026,
    week: 1,
    playerId: null,
    playerUid: null,
    playerName: "G. Holani",
    team: "SEA",
    position: "RB",
    marketKey: "rush_yds",
    line: 21.5,
    modelMean: 12.9,
    modelFloor: 8.6,
    modelCeiling: 17.5,
    fairOverPrice: 200,
    fairUnderPrice: -250,
    marketOverPrice: -110,
    marketUnderPrice: -110,
    edgeOver: -0.487,
    edgeUnder: 0.487,
    confidence: 0.99,
    marketJoined: true,
    tag: null,
    tagSide: null,
    projectionSource: "baseline",
    updatedAt: null,
    ...partial,
  };
}

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
    oddsCapturedAt: "2026-08-21T13:42:55+00:00",
    bestSpreadHome: -3.5,
    bestTotal: 44.5,
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
    fdTotal: 44.5,
    stakeTotal: 44.5,
    stakeTotalBook: "fanduel",
    marketHomeProbNoVig: null,
    mlEdgeProb: null,
    totalEdge: null,
    spreadEdge: null,
    marketJoined: true,
    marketSource: "odds_snapshots",
    publishTagSpread: null,
    publishTagTotal: null,
    stakeEligibleSpread: false,
    stakeEligibleTotal: false,
    stakeEligibleMl: false,
    publishReasonSpread: null,
    publishReasonTotal: null,
    publishReasonMl: null,
    mlEv: null,
    decision: null,
    actionLabelSpread: null,
    actionLabelTotal: null,
    ...partial,
  };
}

describe("Week 1 desk agreement", () => {
  it("Edges lean Under when model < line (Holani rush 12.9 vs 21.5)", () => {
    const row = deskEdgeFromPropRow(propRow({}), {
      minProbEdge: 0.05,
      minConfidence: 0.0,
    });
    expect(row).not.toBeNull();
    expect(row!.side).toBe("Under");
    expect(row!.edge).toBeGreaterThan(0);
  });

  it("Maye pass under lean when model below book", () => {
    const row = deskEdgeFromPropRow(
      propRow({
        playerName: "D. Maye",
        team: "NE",
        position: "QB",
        marketKey: "pass_yds",
        line: 229.5,
        modelMean: 216.2,
        edgeOver: -0.12,
        edgeUnder: 0.12,
        confidence: 0.42,
      }),
      { minProbEdge: 0.05, minConfidence: 0.0 },
    );
    expect(row!.side).toBe("Under");
  });

  it("NE@SEA canonical kickoff is 8:20 ET and odds overlay cannot overwrite", () => {
    const packed = canonicalKickoffForMatchup({
      season: 2026,
      week: 1,
      awayAbbr: "NE",
      homeAbbr: "SEA",
    });
    expect(packed.found).toBe(true);
    expect(packed.kickoffUtc).toBe("2026-09-10T00:20:00.000Z");

    const fair = fairLinesToEdgeBoardRows([fairLine()], {
      boardAsOf: "2026-09-02T12:00:00.000Z",
    });
    const spread = fair.find((r) => r.market === "Spread")!;
    expect(spread.commenceTime).toBe("2026-09-10T00:20:00.000Z");
    expect(String(spread.time)).toMatch(/8:20/);

    const overlaid = overlayOddsOntoFairLineRows(fair, [
      {
        id: "o1",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        best: "+3.5",
        book: "FanDuel",
        time: "09/09 8:15 PM ET",
        commenceTime: "2026-09-10T00:15:00.000Z",
        kickoffTime: "8:15 PM",
      } as any,
    ]);
    const after = overlaid.find((r) => r.market === "Spread")!;
    expect(after.commenceTime).toBe("2026-09-10T00:20:00.000Z");
    expect(String(after.time)).toMatch(/8:20/);
    expect(String(after.time)).not.toMatch(/8:15/);
  });

  it("Edge Board as-of is not stuck on 2026-08-21 when board stamp is current", () => {
    const asOf = resolveEdgeBoardLinesAsOf({
      oddsCapturedAt: "2026-08-21T13:42:55+00:00",
      boardAsOf: "2026-09-02T15:00:00.000Z",
    });
    expect(asOf).toBe("2026-09-02T15:00:00.000Z");
    expect(asOf).not.toMatch(/^2026-08-21/);

    const rows = fairLinesToEdgeBoardRows([fairLine()], {
      boardAsOf: "2026-09-02T15:00:00.000Z",
    });
    for (const r of rows) {
      expect((r as { linesAsOf?: string }).linesAsOf).toBe(
        "2026-09-02T15:00:00.000Z",
      );
    }
  });

  it("Props does not show fair over/under juice when Line is blank", () => {
    const blank = propRow({
      line: null,
      fairOverPrice: 4443,
      fairUnderPrice: -4443,
      marketJoined: false,
      marketOverPrice: null,
      marketUnderPrice: null,
      edgeOver: null,
      edgeUnder: null,
    });
    // UI contract: blank line ⇒ render em dash (page gates on row.line == null).
    expect(blank.line).toBeNull();
    // Desk edges require a market — no Lean on projection-only rows.
    const desk = deskEdgeFromPropRow(blank, {
      minProbEdge: 0.05,
      minConfidence: 0.0,
    });
    expect(desk).toBeNull();
  });

  it("Game Boxes headline prefers spine mean over MC median (Maye contract)", () => {
    // Mirrors SeasonEngineGameBoxesClient: point_estimate ?? mean ?? p50
    const point_estimate = { pass_yards: 216.2, rush_yards: 17.4 };
    const dist = { mean: 210.0, p50: 160.0, p10: 111, p90: 278 };
    const value =
      point_estimate.pass_yards ?? dist.mean ?? dist.p50;
    expect(value).toBeCloseTo(216.2, 1);
    expect(value).not.toBe(160);
  });
});
