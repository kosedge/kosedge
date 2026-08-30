import { describe, expect, it } from "vitest";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import {
  buildNflAtsPickemCard,
  buildNflPickemCard,
  filterPickemWeekLines,
  PICKEM_REG_WEEK_CHIPS,
  parsePickemTab,
  resolveAtsPickemTag,
  resolveAtsSide,
  resolvePickemDefaultWeek,
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
      marketSpreadHome: -(i + 0.5),
      startTime: `2026-09-14T${String(17 + (i % 6)).padStart(2, "0")}:00:00Z`,
      publishTagSpread: "PASS",
      publishTagMl: "PASS",
    });
  });
}

describe("buildNflPickemCard (SU)", () => {
  it("assigns unique ranks 1..N for a 16-game slate (first = 1)", () => {
    const card = buildNflPickemCard(makeSlate(16));
    expect(card).toHaveLength(16);
    const ranks = card.map((p) => p.rank);
    expect(ranks).toEqual([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
    ]);
    expect(card[0]!.rank).toBe(1);
    expect(card[card.length - 1]!.rank).toBe(16);
    expect(new Set(ranks).size).toBe(16);
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
    expect(card.map((p) => p.rank)).toEqual([1, 2, 3, 4]);
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
    expect(card[0]!.rank).toBe(1);
    expect(card[1]!.gameId).toBe("no-prob");
    expect(card[1]!.side).toBe(null);
    expect(card[1]!.pickAbbr).toBe(null);
    expect(card[1]!.winProb).toBe(null);
    expect(card[1]!.rank).toBe(2);
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
    expect(card.map((p) => p.rank)).toEqual([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
    ]);
  });
});

describe("buildNflAtsPickemCard", () => {
  it("picks home when KEI is stronger than the market number", () => {
    const card = buildNflAtsPickemCard([
      line({
        gameId: "home-cover",
        handicapSpreadHome: -4.5,
        spreadHome: -4.5,
        marketSpreadHome: -3.0,
        publishTagSpread: "PASS",
      }),
    ]);
    expect(card[0]!.side).toBe("home");
    expect(card[0]!.pickAbbr).toBe("SEA");
    expect(card[0]!.marketSpreadPick).toBe(-3.0);
    expect(card[0]!.keiSpreadPick).toBe(-4.5);
    expect(card[0]!.atsEdge).toBe(-1.5);
    expect(Math.abs(card[0]!.atsEdge!)).toBe(1.5);
  });

  it("picks away when KEI is weaker than the market number", () => {
    const card = buildNflAtsPickemCard([
      line({
        gameId: "away-cover",
        handicapSpreadHome: -1.0,
        spreadHome: -1.0,
        marketSpreadHome: -3.0,
        publishTagSpread: "PASS",
      }),
    ]);
    expect(card[0]!.side).toBe("away");
    expect(card[0]!.pickAbbr).toBe("NE");
    expect(card[0]!.marketSpreadPick).toBe(3.0);
    expect(card[0]!.keiSpreadPick).toBe(1.0);
    expect(card[0]!.atsEdge).toBe(2.0);
  });

  it("sinks missing market with side null and last ranks", () => {
    const lines = [
      line({
        gameId: "no-mkt",
        handicapSpreadHome: -4,
        marketSpreadHome: null,
        dkSpreadHome: null,
        fdSpreadHome: null,
        stakeSpreadHome: null,
        publishTagSpread: "PLAY",
        startTime: "2026-09-14T13:00:00Z",
      }),
      line({
        gameId: "has-mkt",
        handicapSpreadHome: -3,
        marketSpreadHome: -2,
        publishTagSpread: "PASS",
        startTime: "2026-09-14T20:00:00Z",
      }),
    ];
    const card = buildNflAtsPickemCard(lines);
    expect(card[0]!.gameId).toBe("has-mkt");
    expect(card[0]!.rank).toBe(1);
    expect(card[1]!.gameId).toBe("no-mkt");
    expect(card[1]!.side).toBe(null);
    expect(card[1]!.pickAbbr).toBe(null);
    expect(card[1]!.marketSpreadPick).toBe(null);
    expect(card[1]!.rank).toBe(2);
  });

  it("orders PLAY spread above LEAN above PASS by |edge| inside bucket", () => {
    const lines = [
      line({
        gameId: "pass-big-edge",
        publishTagSpread: "PASS",
        publishTagMl: "PASS",
        handicapSpreadHome: -7,
        marketSpreadHome: -3,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "lean-mid",
        publishTagSpread: "LEAN",
        handicapSpreadHome: -4,
        marketSpreadHome: -3,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "play-small",
        publishTagSpread: "PLAY",
        handicapSpreadHome: -3.5,
        marketSpreadHome: -3,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "play-big",
        publishTagSpread: "PLAY",
        handicapSpreadHome: -6,
        marketSpreadHome: -3,
        startTime: "2026-09-14T20:00:00Z",
      }),
    ];
    const card = buildNflAtsPickemCard(lines);
    expect(card.map((p) => p.gameId)).toEqual([
      "play-big",
      "play-small",
      "lean-mid",
      "pass-big-edge",
    ]);
    expect(card[0]!.rank).toBe(1);
    expect(Math.abs(card[0]!.atsEdge!)).toBe(3);
    expect(card[0]!.tag).toBe("PLAY");
  });

  it("does not promote an ATS row on ML PLAY alone", () => {
    expect(
      resolveAtsPickemTag(
        line({ publishTagSpread: "PASS", publishTagMl: "PLAY" }),
      ),
    ).toBe("PASS");

    const card = buildNflAtsPickemCard([
      line({
        gameId: "ml-play-only",
        publishTagSpread: "PASS",
        publishTagMl: "PLAY",
        handicapSpreadHome: -5,
        marketSpreadHome: -3,
        startTime: "2026-09-14T17:00:00Z",
      }),
      line({
        gameId: "spread-lean",
        publishTagSpread: "LEAN",
        publishTagMl: "PASS",
        handicapSpreadHome: -3.5,
        marketSpreadHome: -3,
        startTime: "2026-09-14T20:00:00Z",
      }),
    ]);
    expect(card.map((p) => p.gameId)).toEqual(["spread-lean", "ml-play-only"]);
    expect(card[0]!.tag).toBe("LEAN");
    expect(card[1]!.tag).toBe("PASS");
  });

  it("sinks zero edge as no ATS pick", () => {
    const resolved = resolveAtsSide(-3, -3);
    expect(resolved.side).toBe(null);
    expect(resolved.atsEdge).toBe(0);

    const card = buildNflAtsPickemCard([
      line({
        gameId: "zero",
        handicapSpreadHome: -3,
        marketSpreadHome: -3,
        publishTagSpread: "PLAY",
        startTime: "2026-09-14T13:00:00Z",
      }),
      line({
        gameId: "edge",
        handicapSpreadHome: -4,
        marketSpreadHome: -3,
        publishTagSpread: "PASS",
        startTime: "2026-09-14T20:00:00Z",
      }),
    ]);
    expect(card[0]!.gameId).toBe("edge");
    expect(card[1]!.gameId).toBe("zero");
    expect(card[1]!.side).toBe(null);
    expect(card[1]!.rank).toBe(2);
  });

  it("ranks 1 as largest |edge| inside the top tag bucket", () => {
    const card = buildNflAtsPickemCard([
      line({
        gameId: "play-small",
        publishTagSpread: "PLAY",
        handicapSpreadHome: -3.2,
        marketSpreadHome: -3,
      }),
      line({
        gameId: "play-large",
        publishTagSpread: "PLAY",
        handicapSpreadHome: -5,
        marketSpreadHome: -3,
      }),
    ]);
    expect(card[0]!.gameId).toBe("play-large");
    expect(card[0]!.rank).toBe(1);
    expect(Math.abs(card[0]!.atsEdge!)).toBeGreaterThan(
      Math.abs(card[1]!.atsEdge!),
    );
  });

  it("prefers stake → DK → FD → consensus and never best-of-books", () => {
    const card = buildNflAtsPickemCard([
      line({
        gameId: "stake",
        handicapSpreadHome: -4,
        stakeSpreadHome: -3.5,
        stakeSpreadBook: "DraftKings",
        dkSpreadHome: -2,
        fdSpreadHome: -1,
        marketSpreadHome: 0,
        bestSpreadHome: -10,
      }),
    ]);
    expect(card[0]!.marketSpreadHome).toBe(-3.5);
    expect(card[0]!.marketSpreadPick).toBe(-3.5);
    expect(card[0]!.stakeBook).toBe("DraftKings");
  });
});

describe("parsePickemTab", () => {
  it("defaults to ats", () => {
    expect(parsePickemTab(undefined)).toBe("ats");
    expect(parsePickemTab("")).toBe("ats");
    expect(parsePickemTab("su")).toBe("su");
    expect(parsePickemTab("ats")).toBe("ats");
  });
});

describe("resolvePickemDefaultWeek", () => {
  it("uses currentWeek when that week has REG rows", () => {
    const lines = [
      line({ gameId: "w1", week: 1 }),
      line({ gameId: "w2", week: 2 }),
    ];
    expect(resolvePickemDefaultWeek(lines, 2)).toBe(2);
  });

  it("falls back to earliest REG week when currentWeek is empty", () => {
    const lines = [
      line({ gameId: "w1", week: 1 }),
      line({ gameId: "w3", week: 3 }),
    ];
    expect(resolvePickemDefaultWeek(lines, 12)).toBe(1);
  });

  it("ignores PRE rows when choosing the default week", () => {
    const lines = [
      line({ gameId: "pre", week: 1, seasonType: "PRE" }),
      line({ gameId: "reg2", week: 2, seasonType: "REG" }),
    ];
    expect(resolvePickemDefaultWeek(lines, 1)).toBe(2);
  });

  it("returns 1 when the payload has no REG rows", () => {
    expect(resolvePickemDefaultWeek([], 0)).toBe(1);
  });
});

describe("PICKEM_REG_WEEK_CHIPS", () => {
  it("is fixed Weeks 1–18 independent of the fair-lines window", () => {
    expect(PICKEM_REG_WEEK_CHIPS).toEqual([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
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

describe("pickem page fair-lines fetch window", () => {
  it("matches nfl-slate (120 ahead / 2 past), not the 200d timeout path", async () => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const src = readFileSync(
      join(__dirname, "../../app/(pro)/pro/nfl/fantasy/pickem/page.tsx"),
      "utf8",
    );
    expect(src).toContain("daysAhead: 120");
    expect(src).toContain("includePastDays: 2");
    expect(src).not.toContain("daysAhead: 200");
    expect(src).not.toContain("FETCH_DAYS_AHEAD");
    expect(src).toContain("PICKEM_REG_WEEK_CHIPS");
  });
});
