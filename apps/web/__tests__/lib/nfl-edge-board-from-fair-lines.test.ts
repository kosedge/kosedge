import { describe, expect, it } from "vitest";
import {
  fairLinesToEdgeBoardRows,
  filterNflCurrentWeekRows,
  filterNflOddsPostedRows,
  filterNflProjectionBackedRows,
  overlayOddsOntoFairLineRows,
} from "@/lib/nfl-edge-board-from-fair-lines";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";

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
    modelVersion: "test",
    simulationCount: 1000,
    projectionCreatedAt: null,
    marketHomeMl: null,
    marketAwayMl: null,
    marketTotal: 44.5,
    marketSpreadHome: -3.0,
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
    marketJoined: true,
    publishTagSpread: "PASS",
    publishTagTotal: "PASS",
    publishTagMl: "PASS",
    ...partial,
  };
}

describe("nfl-edge-board-from-fair-lines", () => {
  it("fills KEINFL + market open/best for every fair-line game", () => {
    const rows = fairLinesToEdgeBoardRows([line({})]);
    expect(rows).toHaveLength(2);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.kei).toBe("-3.5");
    expect(spread.open).toBe("+3"); // away side of market consensus -3 home
    expect(spread.best).toBe("+3"); // falls back to consensus when no best-of-books
    expect(total.kei).toBe("41.3");
    expect(total.best).toBe("44.5");
  });

  it("uses best-of-books for Best Line / Best O/U instead of consensus", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        marketSpreadHome: -3.0,
        marketTotal: 44.5,
        bestSpreadHome: -3.5,
        bestTotal: 45.0,
        bestSpreadBook: "circa",
        bestTotalBook: "fanduel",
        bestSpreadAwayJuice: -105,
        bestSpreadHomeJuice: -115,
        bestTotalOverJuice: -102,
        bestTotalUnderJuice: -118,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBe("+3");
    expect(spread.best).toBe("+3.5");
    expect((spread as any).bookKey).toBe("circa");
    expect((spread as any).bestJuice).toBe("-105");
    expect(total.open).toBe("44.5");
    expect(total.best).toBe("45");
    expect((total as any).bookKey).toBe("fanduel");
    expect((total as any).bestJuice).toBe("-102");
  });

  it("overlays Odds book-specific best onto fair-line rows", () => {
    const base = fairLinesToEdgeBoardRows([line({})]);
    const out = overlayOddsOntoFairLineRows(base, [
      {
        id: "odds-spread",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        open: "+3.5",
        best: "+4.5",
        book: "FanDuel",
        bookKey: "fanduel",
      } as any,
    ]);
    const spread = out.find((r) => r.market === "Spread")!;
    expect(spread.best).toBe("+4.5");
    expect((spread as any).bookKey).toBe("fanduel");
    expect(spread.kei).toBe("-3.5");
  });

  it("does not append PRE / odds-only extras without fair-line KEI", () => {
    const base = fairLinesToEdgeBoardRows([line({})]);
    const out = overlayOddsOntoFairLineRows(base, [
      {
        id: "pre-spread",
        game: "Dallas Cowboys @ Los Angeles Chargers",
        market: "Spread",
        best: "+3",
        bookKey: "draftkings",
        book: "DraftKings",
      } as any,
    ]);
    expect(out).toHaveLength(2);
    expect(out.every((r) => r.game?.includes("Seahawks"))).toBe(true);
  });

  it("leaves Open/Best empty when no sportsbook market (KEI still set)", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        marketJoined: false,
        marketSpreadHome: null,
        marketTotal: null,
        spreadHome: 1.5,
        totalMean: 43.0,
        homeTeam: "Minnesota Vikings",
        awayTeam: "Green Bay Packers",
        homeAbbr: "MIN",
        awayAbbr: "GB",
        gameId: "g2",
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    expect(spread.kei).toBe("+1.5");
    expect(spread.best).toBeUndefined();
    expect(spread.open).toBeUndefined();
  });

  it("filters current week vs odds-posted slate", () => {
    const rows = [
      ...fairLinesToEdgeBoardRows([
        line({ week: 1, marketJoined: true }),
        line({
          week: 2,
          gameId: "g2",
          homeTeam: "Minnesota Vikings",
          awayTeam: "Green Bay Packers",
          homeAbbr: "MIN",
          awayAbbr: "GB",
          marketJoined: true,
          marketSpreadHome: -1,
          marketTotal: 44,
        }),
        line({
          week: 1,
          gameId: "g3",
          homeTeam: "Los Angeles Rams",
          awayTeam: "San Francisco 49ers",
          homeAbbr: "LAR",
          awayAbbr: "SF",
          marketJoined: false,
          marketSpreadHome: null,
          marketTotal: null,
        }),
      ]),
    ];
    // Overlay a sportsbook on week-2 only
    const withBooks = overlayOddsOntoFairLineRows(rows, [
      {
        id: "o1",
        game: "Green Bay Packers @ Minnesota Vikings",
        market: "Spread",
        best: "+1",
        bookKey: "fanduel",
        book: "FanDuel",
      } as any,
      {
        id: "o2",
        game: "Green Bay Packers @ Minnesota Vikings",
        market: "Total",
        best: "44",
        bookKey: "fanduel",
        book: "FanDuel",
      } as any,
    ]);

    const week1 = filterNflCurrentWeekRows(withBooks, 1);
    const week1Games = new Set(week1.map((r) => r.game));
    expect(week1Games.has("New England Patriots @ Seattle Seahawks")).toBe(
      true,
    );
    expect(week1Games.has("San Francisco 49ers @ Los Angeles Rams")).toBe(true);
    expect(week1Games.has("Green Bay Packers @ Minnesota Vikings")).toBe(false);

    const oddsSlate = filterNflOddsPostedRows(withBooks);
    const oddsGames = new Set(oddsSlate.map((r) => r.game));
    // week1 NE@SEA has market bookKey from fair-lines; week2 has FanDuel overlay
    expect(oddsGames.has("New England Patriots @ Seattle Seahawks")).toBe(true);
    expect(oddsGames.has("Green Bay Packers @ Minnesota Vikings")).toBe(true);
    expect(oddsGames.has("San Francisco 49ers @ Los Angeles Rams")).toBe(false);
  });

  it("falls back to nearest upcoming week instead of dumping full board", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({ week: 2, gameId: "w2" }),
      line({
        week: 3,
        gameId: "w3",
        homeTeam: "Minnesota Vikings",
        awayTeam: "Green Bay Packers",
        homeAbbr: "MIN",
        awayAbbr: "GB",
      }),
    ]);
    const filtered = filterNflCurrentWeekRows(rows, 1);
    const games = new Set(filtered.map((r) => r.game));
    expect(games.size).toBe(1);
    expect(games.has("New England Patriots @ Seattle Seahawks")).toBe(true);
    expect(games.has("Green Bay Packers @ Minnesota Vikings")).toBe(false);
  });

  it("drops odds-only rows from projection-backed filter", () => {
    const rows = [
      ...fairLinesToEdgeBoardRows([line({})]),
      {
        id: "pre-only",
        game: "Dallas Cowboys @ Los Angeles Chargers",
        market: "Spread",
        best: "+2.5",
        bookKey: "fanduel",
      } as any,
    ];
    const filtered = filterNflProjectionBackedRows(rows);
    expect(filtered).toHaveLength(2);
    expect(filtered.every((r) => r.kei)).toBe(true);
  });
});
