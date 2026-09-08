/**
 * INC-2026-09-08 — Edge Board / Edges desk customer-truth contract.
 * Full-slate regression: every supported Edge Board sport + desk handicap paths.
 */
import { describe, expect, it } from "vitest";
import {
  EDGE_BOARD_SPORTS,
  auditDeskHandicapRows,
  auditEdgeBoardActionRows,
  formatSelectedSideLineEdge,
  formatSelectedSideProbEdge,
  handicapSelectedSideAdvantage,
  moneylineSelectedSideAdvantage,
  pickEdgeMarketLine,
  reconcileHandicapCustomerEdge,
  reconcileMoneylineCustomerEdge,
  reconcileTotalCustomerEdge,
  scrubActionEdgeMagnitude,
  totalSelectedSideAdvantage,
} from "@/lib/edge-board-customer-truth";
import { deskEdgesFromFairLine } from "@/lib/nfl-edges";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import { deskEdgesFromTodayRow } from "@/lib/mlb-desk-helpers";

function fairLine(partial: Partial<NflFairLineRow> = {}): NflFairLineRow {
  return {
    gameId: "2026-W01-ARI@LAC",
    season: 2026,
    week: 1,
    seasonType: "REG",
    startTime: "2026-09-13T20:25:00.000Z",
    gameDate: "2026-09-13",
    homeTeam: "Los Angeles Chargers",
    awayTeam: "Arizona Cardinals",
    homeAbbr: "LAC",
    awayAbbr: "ARI",
    homeWinProb: 0.75,
    awayWinProb: 0.25,
    spreadHome: -8.31,
    totalMean: 46.32,
    fairHomeMl: -300,
    fairAwayMl: 240,
    handicapSpreadHome: -8.31,
    handicapTotal: 46.32,
    handicapHomeWinProb: 0.75,
    handicapAwayWinProb: 0.25,
    handicapHomeMl: -300,
    handicapAwayMl: 240,
    modelSpreadHome: -7.08,
    modelTotal: 44.2,
    modelHomeWinProb: 0.75,
    modelAwayWinProb: 0.25,
    modelHomeMl: -300,
    modelAwayMl: 240,
    modelEqualsKei: false,
    keiReprice: null,
    modelVersion: "test",
    simulationCount: null,
    projectionCreatedAt: null,
    marketHomeMl: -280,
    marketAwayMl: 230,
    marketTotal: 47.5,
    marketSpreadHome: -9.5,
    openSpreadHome: -10.5,
    openTotal: 46.5,
    oddsCapturedAt: "2026-09-08T16:11:57Z",
    bestSpreadHome: -10.0,
    bestTotal: 47.5,
    bestSpreadBook: "hardrockbet",
    bestTotalBook: "bovada",
    bestSpreadAwayJuice: -110,
    bestSpreadHomeJuice: -110,
    bestTotalOverJuice: 100,
    bestTotalUnderJuice: -120,
    dkSpreadHome: -10.0,
    fdSpreadHome: -9.5,
    stakeSpreadHome: -10.0,
    stakeSpreadBook: "draftkings",
    dkTotal: 47.5,
    fdTotal: 47.5,
    stakeTotal: 47.5,
    stakeTotalBook: "draftkings",
    marketHomeProbNoVig: 0.7,
    mlEdgeProb: -0.0566,
    totalEdge: -1.18,
    spreadEdge: 1.69,
    marketJoined: true,
    publishTagSpread: "LEAN",
    publishTagTotal: "PASS",
    publishTagMl: null,
    decision: null,
    actionLabelSpread: null,
    actionLabelTotal: null,
    ...partial,
  };
}

describe("edge-board customer-truth contract formulas", () => {
  it("handicap: selected-side advantage is abs(fair−market); Home when signed < 0", () => {
    // BAL-style: fair +1.76 vs market +3.5 → Home lean, +1.74 advantage
    const bal = handicapSelectedSideAdvantage({
      fairLine: 1.76,
      marketLine: 3.5,
    });
    expect(bal.side).toBe("Home");
    expect(bal.advantage).toBeCloseTo(1.74, 5);
    expect(bal.advantage).toBeGreaterThan(0);

    // ARI-style: fair −8.31 vs stake −10 → Away lean, +1.69
    const ari = handicapSelectedSideAdvantage({
      fairLine: -8.31,
      marketLine: -10,
    });
    expect(ari.side).toBe("Away");
    expect(ari.advantage).toBeCloseTo(1.69, 5);
  });

  it("totals: Over/Under from signed fair−market; display magnitude positive", () => {
    const under = totalSelectedSideAdvantage({
      fairTotal: 46.32,
      marketTotal: 47.5,
    });
    expect(under.side).toBe("Under");
    expect(under.advantage).toBeCloseTo(1.18, 5);

    const over = totalSelectedSideAdvantage({
      fairTotal: 50,
      marketTotal: 47.5,
    });
    expect(over.side).toBe("Over");
    expect(over.advantage).toBeCloseTo(2.5, 5);
  });

  it("moneyline: uses prob edge — never abs(American fair − American market)", () => {
    const away = moneylineSelectedSideAdvantage({ signedProbEdge: -0.0566 });
    expect(away.side).toBe("Away");
    expect(away.advantage).toBeCloseTo(0.0566, 5);
    expect(formatSelectedSideProbEdge(away.advantage)).toBe("+5.7pp");
  });

  it("fail closed when claimed edge disagrees with abs(fair−market)", () => {
    // Customer ARI bug: consensus −9.5 painted with stake edge 1.69
    const gap = reconcileHandicapCustomerEdge({
      fairLine: -8.31,
      marketLine: -9.5,
      claimedEdge: 1.69,
    });
    expect(gap.status).toBe("DATA_GAP");
    expect(gap.advantage).toBeNull();

    const ok = reconcileHandicapCustomerEdge({
      fairLine: -8.31,
      marketLine: -10,
      claimedEdge: 1.69,
    });
    expect(ok.status).toBe("ok");
    expect(ok.advantage).toBeCloseTo(1.69, 5);
    expect(ok.side).toBe("Away");
  });

  it("formats selected-side line edge as positive magnitude only", () => {
    expect(formatSelectedSideLineEdge(-1.74, "pts")).toBe("+1.7 pts");
    expect(formatSelectedSideLineEdge(1.69, "pts")).toBe("+1.7 pts");
  });

  it("pickEdgeMarketLine prefers stake → DK → FD → consensus → best", () => {
    expect(
      pickEdgeMarketLine({
        stake: -10,
        dk: -10,
        fd: -9.5,
        market: -9.5,
        best: -10,
      }),
    ).toBe(-10);
    expect(
      pickEdgeMarketLine({
        stake: null,
        dk: null,
        fd: -9.5,
        market: -9.5,
        best: -10,
      }),
    ).toBe(-9.5);
  });

  it("scrubActionEdgeMagnitude fails closed on mismatch", () => {
    expect(
      scrubActionEdgeMagnitude({
        fair: -8.31,
        market: -9.5,
        edgeMagnitude: 1.69,
        kind: "handicap",
      }),
    ).toBeUndefined();
    expect(
      scrubActionEdgeMagnitude({
        fair: -8.31,
        market: -10,
        edgeMagnitude: 1.69,
        kind: "handicap",
      }),
    ).toBeCloseTo(1.69, 5);
  });
});

describe("NFL deskEdgesFromFairLine customer-truth (ARI / BAL / NYJ class)", () => {
  it("ARI @ LAC paints stake market with matching positive edge (not consensus −9.5 + 1.7)", () => {
    const rows = deskEdgesFromFairLine(fairLine(), {
      minProbEdge: 0.02,
      minLineEdge: 1.0,
    });
    const spread = rows.find((r) => r.marketType === "spread");
    expect(spread).toBeTruthy();
    expect(spread!.marketLine).toBe("-10.00");
    expect(spread!.edge).toBeCloseTo(1.69, 5);
    expect(spread!.edge).toBeGreaterThan(0);
    expect(spread!.edgeDisplay).toBe("+1.7 pts");
    expect(spread!.side).toBe("Away");
    // Arithmetic identity
    expect(Math.abs(-8.31 - -10)).toBeCloseTo(spread!.edge, 5);
  });

  it("BAL-class Home lean displays positive magnitude (never green-negative)", () => {
    const rows = deskEdgesFromFairLine(
      fairLine({
        gameId: "bal-ind",
        awayAbbr: "BAL",
        homeAbbr: "IND",
        spreadHome: 1.76,
        handicapSpreadHome: 1.76,
        marketSpreadHome: 3.5,
        dkSpreadHome: 3.5,
        fdSpreadHome: 3.5,
        stakeSpreadHome: 3.5,
        bestSpreadHome: 3.5,
        spreadEdge: -1.74,
        mlEdgeProb: 0.05,
        totalEdge: -0.1,
      }),
      { minProbEdge: 0.02, minLineEdge: 1.0 },
    );
    const spread = rows.find((r) => r.marketType === "spread");
    expect(spread!.side).toBe("Home");
    expect(spread!.edge).toBeGreaterThan(0);
    expect(spread!.edgeDisplay.startsWith("-")).toBe(false);
    expect(spread!.edgeDisplay).toBe("+1.7 pts");
    expect(spread!.marketLine).toBe("+3.50");
  });

  it("fail closed when only consensus is available and disagrees with claimed edge", () => {
    const rows = deskEdgesFromFairLine(
      fairLine({
        // Force consensus-only paint that disagrees with claimed stake edge.
        stakeSpreadHome: null,
        dkSpreadHome: null,
        fdSpreadHome: null,
        bestSpreadHome: null,
        marketSpreadHome: -9.5,
        spreadEdge: 1.69,
      }),
      { minProbEdge: 0.02, minLineEdge: 1.0 },
    );
    expect(rows.find((r) => r.marketType === "spread")).toBeUndefined();
  });

  it("totals use stake market + positive magnitude", () => {
    const rows = deskEdgesFromFairLine(
      fairLine({
        totalEdge: -1.97,
        totalMean: 45.53,
        marketTotal: 47.0,
        stakeTotal: 47.5,
        dkTotal: 47.5,
        fdTotal: 47.5,
        bestTotal: 47.5,
        spreadEdge: null,
        mlEdgeProb: null,
      }),
      { minProbEdge: 0.02, minLineEdge: 1.0 },
    );
    const total = rows.find((r) => r.marketType === "total");
    expect(total!.side).toBe("Under");
    expect(total!.marketLine).toBe("47.5");
    expect(total!.edge).toBeCloseTo(1.97, 5);
    expect(total!.edgeDisplay).toBe("+2.0 pts");
  });

  it("ML uses prob formula with positive selected-side pp", () => {
    const rows = deskEdgesFromFairLine(
      fairLine({
        mlEdgeProb: -0.0566,
        spreadEdge: null,
        totalEdge: null,
      }),
      { minProbEdge: 0.02, minLineEdge: 1.0 },
    );
    const ml = rows.find((r) => r.marketType === "ml");
    expect(ml!.side).toBe("Away");
    expect(ml!.edge).toBeGreaterThan(0);
    expect(ml!.edgeDisplay).toBe("+5.7pp");
  });
});

describe("MLB desk customer-truth", () => {
  it("total Under shows positive runs magnitude", () => {
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
    const total = rows.find((r) => r.marketType === "total");
    expect(total!.side).toBe("Under");
    expect(total!.edge).toBeGreaterThan(0);
    expect(total!.edgeDisplay).toBe("+0.6 runs");
  });

  it("fail closed when total fair/market/edge disagree", () => {
    const rows = deskEdgesFromTodayRow(
      {
        game_id: "g1",
        home_team: "Yankees",
        away_team: "Red Sox",
        fair_total: 8.4,
        market_total: 9.0,
        total_edge: -2.0, // disagrees with |8.4−9.0|=0.6
        quality_score: 70,
      },
      { minProbEdge: 0.02, minLineEdge: 0.5, minQuality: 60 },
    );
    expect(rows.find((r) => r.marketType === "total")).toBeUndefined();
  });
});

describe("full-slate audits for every Edge Board sport", () => {
  it("lists all seven Edge Board sports", () => {
    expect(EDGE_BOARD_SPORTS).toEqual([
      "nfl",
      "cfb",
      "nba",
      "nhl",
      "mlb",
      "wnba",
      "ncaam",
    ]);
  });

  it("desk auditor flags sign + arithmetic on a full synthetic multi-sport slate", () => {
    for (const sport of EDGE_BOARD_SPORTS) {
      const bad = auditDeskHandicapRows({
        sport,
        rows: [
          {
            id: `${sport}-bad-sign`,
            marketType: "spread",
            kosedgeLine: "+1.76",
            marketLine: "+3.50",
            edge: -1.74,
            edgeDisplay: "-1.7 pts",
            side: "Home",
          },
          {
            id: `${sport}-bad-arith`,
            marketType: "spread",
            kosedgeLine: "-8.31",
            marketLine: "-9.50",
            edge: 1.69,
            edgeDisplay: "+1.7 pts",
            side: "Away",
          },
          {
            id: `${sport}-ok`,
            marketType: "spread",
            kosedgeLine: "-8.31",
            marketLine: "-10.00",
            edge: 1.69,
            edgeDisplay: "+1.7 pts",
            side: "Away",
          },
        ],
      });
      expect(bad.handicapRows).toBe(3);
      expect(bad.signInconsistencies).toBe(1);
      expect(bad.arithmeticInconsistencies).toBe(1);
    }
  });

  it("edge-board auditor scans full slate rows per sport with zero tolerance for neg magnitude / arith mismatch", () => {
    for (const sport of EDGE_BOARD_SPORTS) {
      const slate = [
        {
          id: `${sport}-1-spread`,
          game: "A @ B",
          market: "Spread",
          fairLine: -3.0,
          decisionMarketLine: -3.5,
          edgeMagnitude: 0.5,
        },
        {
          id: `${sport}-1-total`,
          game: "A @ B",
          market: "Total",
          fairLine: 44.0,
          decisionMarketLine: 45.5,
          edgeMagnitude: 1.5,
        },
        {
          id: `${sport}-2-spread`,
          game: "C @ D",
          market: "Spread",
          fairLine: 1.76,
          decisionMarketLine: 3.5,
          edgeMagnitude: 1.74,
        },
      ];
      const summary = auditEdgeBoardActionRows({ sport, rows: slate });
      expect(summary.signInconsistencies).toBe(0);
      expect(summary.arithmeticInconsistencies).toBe(0);

      const poisoned = auditEdgeBoardActionRows({
        sport,
        rows: [
          ...slate,
          {
            id: `${sport}-poison`,
            game: "ARI @ LAC",
            market: "Spread",
            fairLine: -8.31,
            decisionMarketLine: -9.5,
            edgeMagnitude: 1.69,
          },
        ],
      });
      expect(poisoned.arithmeticInconsistencies).toBe(1);
    }
  });

  it("reconcileTotalCustomerEdge DATA_GAP path", () => {
    expect(
      reconcileTotalCustomerEdge({
        fairTotal: 46.8,
        marketTotal: 50,
        claimedEdge: -2.74,
      }).status,
    ).toBe("DATA_GAP");
    expect(
      reconcileTotalCustomerEdge({
        fairTotal: 46.8,
        marketTotal: 49.5,
        claimedEdge: -2.7,
      }).status,
    ).toBe("ok");
  });

  it("reconcileMoneylineCustomerEdge keeps Home/Away from signed prob", () => {
    expect(reconcileMoneylineCustomerEdge({ signedProbEdge: 0.04 }).side).toBe(
      "Home",
    );
    expect(reconcileMoneylineCustomerEdge({ signedProbEdge: -0.04 }).side).toBe(
      "Away",
    );
  });
});
