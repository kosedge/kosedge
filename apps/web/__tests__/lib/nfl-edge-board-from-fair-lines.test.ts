import { describe, expect, it } from "vitest";
import {
  fairLinesToEdgeBoardRows,
  filterNflCurrentWeekRows,
  filterNflOddsPostedRows,
  filterNflProjectionBackedRows,
  filterNflStrictWeekRows,
  overlayOddsOntoFairLineRows,
  syncEdgeBoardActionsWithCurrent,
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

describe("nfl-edge-board-from-fair-lines", () => {
  it("attaches PLAY action + play-to ladder for a large model edge", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        week: 8,
        modelSpreadHome: -7,
        spreadHome: -7,
        handicapSpreadHome: -7,
        marketSpreadHome: -3,
        bestSpreadHome: -3,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    expect((spread as { actionLabel?: string }).actionLabel).toMatch(
      /PLAY|BEST VALUE/,
    );
    expect((spread as { playToNotes?: string }).playToNotes).toBeTruthy();
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(4);
  });

  it("tags PLAY against DK/FD stake close, not the shop best", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        week: 8,
        modelSpreadHome: -7,
        spreadHome: -7,
        handicapSpreadHome: -7,
        marketSpreadHome: -6.5,
        bestSpreadHome: -3,
        dkSpreadHome: -6.5,
        stakeSpreadHome: -6.5,
        stakeSpreadBook: "draftkings",
        decision: null,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(
      0.5,
    );
    expect((spread as { actionLabel?: string }).actionLabel).toBe("PASS");
    expect(spread.best).toBe("+3");
  });

  it("uses Current (best) for Action when dedicated Mkt / stake is empty", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        week: 8,
        modelSpreadHome: -7,
        spreadHome: -7,
        handicapSpreadHome: -7,
        marketSpreadHome: null,
        bestSpreadHome: -3,
        stakeSpreadHome: null,
        dkSpreadHome: null,
        fdSpreadHome: null,
        decision: null,
        actionLabelSpread: null,
        actionLabelTotal: null,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    expect(spread.best).toBe("+3");
    expect((spread as { decisionMarketLine?: number }).decisionMarketLine).toBe(
      -3,
    );
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(4);
    expect((spread as { actionLabel?: string }).actionLabel).toMatch(
      /PLAY|BEST VALUE/,
    );
  });

  it("syncs Action after Odds overlay fills Current onto a Mkt-empty decision", () => {
    // Server-style decision: PASS · Edge 0.0 · Mkt — (missing market).
    const fair = fairLinesToEdgeBoardRows([
      line({
        week: 1,
        spreadHome: -4.2,
        handicapSpreadHome: -4.2,
        modelSpreadHome: -4.2,
        marketSpreadHome: null,
        bestSpreadHome: null,
        stakeSpreadHome: null,
        marketTotal: null,
        bestTotal: null,
        totalMean: 43.3,
        handicapTotal: 43.3,
        decision: {
          doctrine: "We bet prices, not teams.",
          week: 1,
          weekRegime: "early",
          spread: {
            market: "spread",
            actionLabel: "PASS",
            pointGrade: "PASS",
            edgeMagnitude: 0,
            modelConfidence: {
              score: 0.72,
              band: "HIGH",
              factors: {},
              unresolvedFlags: [],
            },
            coverProb: null,
            coverGrade: null,
            playTo: null,
            marketConfirmation: {
              modelFair: -4.2,
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
            priceStillAvailable: false,
            numericalEdge: false,
            confidenceOk: false,
            reason: "missing_fair_or_market",
            week: 1,
            weekRegime: "early",
            fairLine: -4.2,
            marketLine: null,
          },
          total: {
            market: "total",
            actionLabel: "PASS",
            pointGrade: "PASS",
            edgeMagnitude: 0,
            modelConfidence: {
              score: 0.72,
              band: "HIGH",
              factors: {},
              unresolvedFlags: [],
            },
            coverProb: null,
            coverGrade: null,
            playTo: null,
            marketConfirmation: {
              modelFair: 43.3,
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
            priceStillAvailable: false,
            numericalEdge: false,
            confidenceOk: false,
            reason: "missing_fair_or_market",
            week: 1,
            weekRegime: "early",
            fairLine: 43.3,
            marketLine: null,
          },
          edgeMagnitudeSpread: 0,
          edgeMagnitudeTotal: 0,
          modelConfidence: {
            score: 0.72,
            band: "HIGH",
            factors: {},
            unresolvedFlags: [],
          },
          actionLabelSpread: "PASS",
          actionLabelTotal: "PASS",
        },
        actionLabelSpread: "PASS",
        actionLabelTotal: "PASS",
      }),
    ]);
    // Without Current, Action edge stays honest-empty (not 0.0 theater).
    const pre = fair.find((r) => r.market === "Spread")!;
    expect((pre as { edgeMagnitude?: number }).edgeMagnitude).toBeUndefined();

    const overlaid = overlayOddsOntoFairLineRows(fair, [
      {
        id: "o1",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        best: "+3.5",
        bookKey: "fanduel",
        book: "FanDuel",
      } as any,
      {
        id: "o2",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Total",
        best: "44.5",
        bookKey: "fanduel",
        book: "FanDuel",
      } as any,
    ]);
    const synced = syncEdgeBoardActionsWithCurrent(overlaid);
    const spread = synced.find((r) => r.market === "Spread")!;
    const total = synced.find((r) => r.market === "Total")!;
    expect(spread.best).toBe("+3.5");
    expect(total.best).toBe("44.5");
    // KEI −4.2 vs Current −3.5 → |0.7|; Action Mkt must match Current.
    expect((spread as { decisionMarketLine?: number }).decisionMarketLine).toBe(
      -3.5,
    );
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(
      0.7,
      1,
    );
    // Week-1 early band: 0.7 < 1.25 → PASS is correct; magnitude must not be 0.0.
    expect((spread as { actionLabel?: string }).actionLabel).toBe("PASS");
    expect((total as { decisionMarketLine?: number }).decisionMarketLine).toBe(
      44.5,
    );
    expect((total as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(
      1.2,
      1,
    );
  });

  it("fills KEINFL + current market; open only from first-capture fields", () => {
    const rows = fairLinesToEdgeBoardRows([line({})]);
    expect(rows).toHaveLength(2);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.kei).toBe("-3.5");
    // No openSpreadHome → open stays blank (never invent open = current).
    expect(spread.open).toBeUndefined();
    expect(spread.best).toBe("+3"); // current = consensus when no best-of-books
    expect(total.kei).toBe("41.3");
    expect(total.open).toBeUndefined();
    expect(total.best).toBe("44.5");
    expect((spread as { modelKei?: string }).modelKei).toBe("-3.5");
    // Decision Engine action layer attached (Model fair vs market).
    // Week-1 early regime: |−3.5 − (−3.0)| = 0.5 → PASS (< 1.5).
    expect((spread as { actionLabel?: string }).actionLabel).toBe("PASS");
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(
      0.5,
    );
    expect(
      (spread as { modelConfidenceBand?: string }).modelConfidenceBand,
    ).toBeTruthy();
    expect((spread as { weekRegime?: string }).weekRegime).toBe("early");
  });

  it("keeps open distinct from current when opening fields are present", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        openSpreadHome: -2.5,
        openTotal: 43.5,
        marketSpreadHome: -3.5,
        bestSpreadHome: -3.5,
        marketTotal: 48.5,
        bestTotal: 48.5,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBe("+2.5");
    expect(spread.best).toBe("+3.5");
    expect(total.open).toBe("43.5");
    expect(total.best).toBe("48.5");
  });

  it("paints NE@SEA Current from snapshot-backed fair-lines without copying Open", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        week: 1,
        spreadHome: -4.22,
        handicapSpreadHome: -4.22,
        totalMean: 43.33,
        handicapTotal: 43.33,
        openSpreadHome: -3.0,
        openTotal: 44.0,
        marketSpreadHome: -3.5,
        marketTotal: 44.5,
        bestSpreadHome: -3.5,
        bestTotal: 44.5,
        marketJoined: true,
        decision: null,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBe("+3");
    expect(spread.best).toBe("+3.5");
    expect(spread.open).not.toBe(spread.best);
    expect(total.open).toBe("44");
    expect(total.best).toBe("44.5");
    expect((spread as { decisionMarketLine?: number }).decisionMarketLine).toBe(
      -3.5,
    );
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(
      0.72,
      1,
    );
    expect((spread as { actionLabel?: string }).actionLabel).toBe("PASS");
    expect((total as { decisionMarketLine?: number }).decisionMarketLine).toBe(
      44.5,
    );
  });

  it("overlay updates current but does not overwrite open", () => {
    const fair = fairLinesToEdgeBoardRows([
      line({
        openSpreadHome: -2.5,
        marketSpreadHome: -3,
        bestSpreadHome: -3,
      }),
    ]);
    const overlaid = overlayOddsOntoFairLineRows(fair, [
      {
        id: "o1",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        open: "+7",
        best: "+4",
        bookKey: "fanduel",
        book: "FanDuel",
      } as any,
    ]);
    const spread = overlaid.find((r) => r.market === "Spread")!;
    expect(spread.open).toBe("+2.5");
    expect(spread.best).toBe("+4");
  });

  it("attaches modelKei from pre-blend model fields while kei stays handicap", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        spreadHome: -2.0,
        handicapSpreadHome: -2.0,
        modelSpreadHome: -4.2,
        totalMean: 46.5,
        handicapTotal: 46.5,
        modelTotal: 43.1,
        modelEqualsKei: false,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.kei).toBe("-2");
    expect((spread as { modelKei?: string }).modelKei).toBe("-4.2");
    expect(total.kei).toBe("46.5");
    expect((total as { modelKei?: string }).modelKei).toBe("43.1");
  });

  it("uses best-of-books for Current Line / Current O/U instead of consensus", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        marketSpreadHome: -3.0,
        marketTotal: 44.5,
        openSpreadHome: -3.0,
        openTotal: 44.5,
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
        handicapSpreadHome: 1.5,
        totalMean: 43.0,
        handicapTotal: 43.0,
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

  it("strict Week 1 filter stays empty — no nearest-week fallthrough", () => {
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
      line({
        week: 1,
        gameId: "pre1",
        seasonType: "PRE",
        homeTeam: "Buffalo Bills",
        awayTeam: "Houston Texans",
        homeAbbr: "BUF",
        awayAbbr: "HOU",
      }),
    ]);
    const week1 = filterNflStrictWeekRows(rows, 1);
    expect(week1).toHaveLength(0);
  });

  it("strict Week 1 keeps REG week-1 games and drops PRE", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({ week: 1, gameId: "reg1" }),
      line({
        week: 1,
        gameId: "pre1",
        seasonType: "PRE",
        homeTeam: "Buffalo Bills",
        awayTeam: "Houston Texans",
        homeAbbr: "BUF",
        awayAbbr: "HOU",
      }),
      line({
        week: 2,
        gameId: "w2",
        homeTeam: "Minnesota Vikings",
        awayTeam: "Green Bay Packers",
        homeAbbr: "MIN",
        awayAbbr: "GB",
      }),
    ]);
    const week1 = filterNflStrictWeekRows(rows, 1);
    const games = new Set(week1.map((r) => r.game));
    expect(games.has("New England Patriots @ Seattle Seahawks")).toBe(true);
    expect(games.has("Houston Texans @ Buffalo Bills")).toBe(false);
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

  it("blanks 3.8 / 2.4-class Current and does not Action against it", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        week: 1,
        spreadHome: -4.22,
        handicapSpreadHome: -4.22,
        totalMean: 43.33,
        handicapTotal: 43.33,
        openSpreadHome: -3.5,
        openTotal: 44.5,
        marketSpreadHome: -3.58,
        marketTotal: 44.42,
        bestSpreadHome: -3.58,
        bestTotal: 44.42,
        marketJoined: true,
        decision: null,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    const total = rows.find((r) => r.market === "Total")!;
    expect(spread.open).toBe("+3.5");
    expect(total.open).toBe("44.5");
    expect(spread.best).toBeUndefined();
    expect(total.best).toBeUndefined();
    expect(
      (spread as { decisionMarketLine?: number | null }).decisionMarketLine,
    ).toBeNull();
    expect(
      (spread as { edgeMagnitude?: number }).edgeMagnitude,
    ).toBeUndefined();
  });

  it("keeps posted-shaped Current (−3.5 / 44.5) and Actions against it", () => {
    const rows = fairLinesToEdgeBoardRows([
      line({
        week: 1,
        spreadHome: -4.22,
        handicapSpreadHome: -4.22,
        openSpreadHome: -3.5,
        marketSpreadHome: -3.5,
        bestSpreadHome: -3.5,
        marketTotal: 44.5,
        bestTotal: 44.5,
        decision: null,
      }),
    ]);
    const spread = rows.find((r) => r.market === "Spread")!;
    expect(spread.best).toBe("+3.5");
    expect(spread.open).toBe("+3.5");
    expect((spread as { decisionMarketLine?: number }).decisionMarketLine).toBe(
      -3.5,
    );
    expect((spread as { edgeMagnitude?: number }).edgeMagnitude).toBeCloseTo(
      0.72,
      1,
    );
  });

  it("does not overlay garbage Current onto a valid fair-line row", () => {
    const fair = fairLinesToEdgeBoardRows([
      line({
        openSpreadHome: -3.5,
        marketSpreadHome: -3.5,
        bestSpreadHome: -3.5,
      }),
    ]);
    const overlaid = overlayOddsOntoFairLineRows(fair, [
      {
        id: "o1",
        game: "New England Patriots @ Seattle Seahawks",
        market: "Spread",
        best: "+3.8",
        bookKey: "fanduel",
        book: "FanDuel",
      } as any,
    ]);
    const spread = overlaid.find((r) => r.market === "Spread")!;
    expect(spread.open).toBe("+3.5");
    expect(spread.best).toBe("+3.5");
  });
});
