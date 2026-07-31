import { describe, expect, it } from "vitest";
import { keiGamesFromMlbFairLines } from "@/lib/mlb-kei-from-fair-lines";
import type { MlbFairLineRow } from "@/lib/mlb-fair-lines-format";

describe("keiGamesFromMlbFairLines", () => {
  it("maps fair spread and total into KEI games", () => {
    const lines: MlbFairLineRow[] = [
      {
        gameId: "g1",
        gameDate: "2026-07-31",
        startTime: "2026-07-31T18:21:00Z",
        homeTeam: "Chicago Cubs",
        awayTeam: "New York Yankees",
        homeWinProb: 0.55,
        fairHomeMl: -120,
        fairAwayMl: 100,
        totalMean: 8.7,
        fairTotal: 9.0,
        fairSpreadHome: -1.5,
        runLineCoverProbHome: 0.48,
        marginMean: -0.4,
        projectedAt: null,
        modelVersion: "mlb-v1",
      },
    ];
    const games = keiGamesFromMlbFairLines(lines);
    expect(games).toHaveLength(1);
    expect(games[0]?.homeTeam).toBe("Chicago Cubs");
    expect(games[0]?.awayTeam).toBe("New York Yankees");
    expect(games[0]?.projSpreadHome).toBe(-1.5);
    expect(games[0]?.projTotal).toBe(9.0);
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
});
