import { describe, expect, it } from "vitest";
import { keiGamesFromMlbFairLines } from "@/lib/mlb-kei-from-fair-lines";
import type { MlbFairLineRow } from "@/lib/mlb-fair-lines-format";

describe("keiGamesFromMlbFairLines", () => {
  it("maps handicap into KEI proj* and preserves distinct model fields", () => {
    const lines: MlbFairLineRow[] = [
      {
        gameId: "g1",
        gameDate: "2026-07-31",
        startTime: "2026-07-31T18:21:00Z",
        homeTeam: "Chicago Cubs",
        awayTeam: "New York Yankees",
        homeWinProb: 0.58,
        fairHomeMl: -130,
        fairAwayMl: 110,
        totalMean: 9.0,
        fairTotal: 9.0,
        fairSpreadHome: -1.5,
        runLineCoverProbHome: 0.48,
        marginMean: -0.4,
        projectedAt: null,
        modelVersion: "mlb-v1",
        handicapHomeWinProb: 0.58,
        handicapHomeMl: -130,
        handicapAwayMl: 110,
        handicapTotal: 9.0,
        handicapSpreadHome: -1.5,
        modelHomeWinProb: 0.55,
        modelHomeMl: -120,
        modelAwayMl: 100,
        modelTotal: 8.5,
        modelSpreadHome: -1.5,
      },
    ];
    const games = keiGamesFromMlbFairLines(lines);
    expect(games).toHaveLength(1);
    expect(games[0]?.homeTeam).toBe("Chicago Cubs");
    expect(games[0]?.awayTeam).toBe("New York Yankees");
    // Handicap → edgeboard aliases
    expect(games[0]?.projSpreadHome).toBe(-1.5);
    expect(games[0]?.projTotal).toBe(9.0);
    expect(games[0]?.projHomeMl).toBe(-130);
    expect(games[0]?.projAwayMl).toBe(110);
    expect(games[0]?.homeWinProb).toBe(0.58);
    expect(games[0]?.handicapHomeMl).toBe(-130);
    // Model remains research fair
    expect(games[0]?.modelHomeMl).toBe(-120);
    expect(games[0]?.modelHomeWinProb).toBe(0.55);
    expect(games[0]?.modelTotal).toBe(8.5);
  });

  it("falls back to totalMean when fairTotal missing", () => {
    const lines: MlbFairLineRow[] = [
      {
        gameId: "g2",
        gameDate: null,
        startTime: null,
        homeTeam: "Home",
        awayTeam: "Away",
        homeWinProb: null,
        fairHomeMl: null,
        fairAwayMl: null,
        totalMean: 7.5,
        fairTotal: null,
        fairSpreadHome: null,
        runLineCoverProbHome: null,
        marginMean: null,
        projectedAt: null,
        modelVersion: "mlb-v1",
      },
    ];
    expect(keiGamesFromMlbFairLines(lines)[0]?.projTotal).toBe(7.5);
  });

  it("identity: model equals handicap when model fields absent", () => {
    const lines: MlbFairLineRow[] = [
      {
        gameId: "g3",
        gameDate: null,
        startTime: null,
        homeTeam: "Home",
        awayTeam: "Away",
        homeWinProb: 0.51,
        fairHomeMl: -105,
        fairAwayMl: -105,
        totalMean: 8.0,
        fairTotal: 8.0,
        fairSpreadHome: -1.5,
        runLineCoverProbHome: null,
        marginMean: null,
        projectedAt: null,
        modelVersion: "mlb-v1",
      },
    ];
    const g = keiGamesFromMlbFairLines(lines)[0]!;
    expect(g.modelHomeMl).toBe(g.handicapHomeMl);
    expect(g.modelHomeWinProb).toBe(g.handicapHomeWinProb);
    expect(g.modelTotal).toBe(g.handicapTotal);
  });
});
