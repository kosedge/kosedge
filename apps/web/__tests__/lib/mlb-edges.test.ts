import { describe, expect, it } from "vitest";
import {
  deskEdgesFromTodayRow,
  deskRunLineFromFairLine,
} from "@/lib/mlb-desk-helpers";
import type { MlbFairLineRow } from "@/lib/mlb-fair-lines-format";

describe("mlb edges desk helpers", () => {
  it("builds ML and total desk rows above thresholds", () => {
    const rows = deskEdgesFromTodayRow(
      {
        game_id: "g1",
        home_team: "Yankees",
        away_team: "Red Sox",
        fair_home_ml: -130,
        market_home_ml: -110,
        market_away_ml: -105,
        ml_edge_prob: 0.035,
        fair_total: 8.4,
        market_total: 9.0,
        total_edge: -0.6,
        quality_score: 70,
        recommended_stake_fraction: 0.012,
      },
      { minProbEdge: 0.02, minLineEdge: 0.5, minQuality: 60 },
    );
    expect(rows.map((r) => r.marketType)).toEqual(["ml", "total"]);
    expect(rows[0]?.side).toBe("Home");
    expect(rows[1]?.side).toBe("Under");
  });

  it("filters by quality floor", () => {
    const rows = deskEdgesFromTodayRow(
      {
        game_id: "g1",
        home_team: "Yankees",
        away_team: "Red Sox",
        ml_edge_prob: 0.05,
        fair_home_ml: -120,
        market_home_ml: -105,
        quality_score: 40,
      },
      { minProbEdge: 0.02, minLineEdge: 0.5, minQuality: 62 },
    );
    expect(rows).toHaveLength(0);
  });

  it("surfaces run-line lean from cover probability", () => {
    const fair: MlbFairLineRow = {
      gameId: "g2",
      gameDate: "2026-07-24",
      startTime: null,
      homeTeam: "Dodgers",
      awayTeam: "Giants",
      homeWinProb: 0.58,
      fairHomeMl: -140,
      fairAwayMl: 120,
      totalMean: 8.2,
      fairTotal: 8.1,
      fairSpreadHome: -1.5,
      runLineCoverProbHome: 0.61,
      marginMean: 0.8,
      projectedAt: null,
      modelVersion: "mlb-test",
    };
    const row = deskRunLineFromFairLine(fair, { minCoverLean: 0.02 });
    expect(row?.marketType).toBe("run_line");
    expect(row?.side).toBe("Home −1.5");
  });
});
