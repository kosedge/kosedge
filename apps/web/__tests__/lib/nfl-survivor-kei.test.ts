import { describe, expect, it } from "vitest";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import {
  avgLockedKeiWp,
  keiWinProbForTeam,
  overlaySurvivorPickWithKei,
  overlaySurvivorPlanWithKei,
  sortSurvivorLeansByDisplayWp,
} from "@/lib/nfl-survivor-kei";

function line(partial: Partial<NflFairLineRow>): NflFairLineRow {
  return {
    gameId: "g1",
    season: 2026,
    week: 1,
    seasonType: "REG",
    startTime: "2026-09-07T02:15:00Z",
    gameDate: "2026-09-06",
    homeTeam: "Home",
    awayTeam: "Away",
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
    marketTotal: null,
    marketSpreadHome: null,
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
    marketJoined: false,
    publishTagSpread: "PASS",
    publishTagTotal: "PASS",
    publishTagMl: "PASS",
    decision: null,
    actionLabelSpread: null,
    actionLabelTotal: null,
    ...partial,
  };
}

/** Week 1 2026 REG slate slice — Melbourne SF @ LAR, ARI @ LAC. Not SF–LAC. */
const week1Lines: NflFairLineRow[] = [
  line({
    gameId: "sf-at-lar-w1",
    week: 1,
    homeAbbr: "LAR",
    awayAbbr: "SF",
    homeTeam: "Los Angeles Rams",
    awayTeam: "San Francisco 49ers",
    handicapHomeWinProb: 0.58,
    handicapAwayWinProb: 0.42,
    homeWinProb: 0.58,
    awayWinProb: 0.42,
    handicapSpreadHome: -2.5,
    startTime: "2026-09-05T09:30:00Z",
  }),
  line({
    gameId: "ari-at-lac-w1",
    week: 1,
    homeAbbr: "LAC",
    awayAbbr: "ARI",
    homeTeam: "Los Angeles Chargers",
    awayTeam: "Arizona Cardinals",
    handicapHomeWinProb: 0.78,
    handicapAwayWinProb: 0.22,
    homeWinProb: 0.78,
    awayWinProb: 0.22,
    handicapSpreadHome: -10.5,
    startTime: "2026-09-07T20:05:00Z",
  }),
  // Preseason / Week 15 noise must never join Week 1.
  line({
    gameId: "sf-vs-lac-w15",
    week: 15,
    homeAbbr: "LAC",
    awayAbbr: "SF",
    handicapHomeWinProb: 0.55,
    handicapAwayWinProb: 0.45,
    homeWinProb: 0.55,
    awayWinProb: 0.45,
  }),
  line({
    gameId: "sf-vs-lac-pre",
    week: 1,
    seasonType: "PRE",
    homeAbbr: "LAC",
    awayAbbr: "SF",
    handicapHomeWinProb: 0.51,
    handicapAwayWinProb: 0.49,
    homeWinProb: 0.51,
    awayWinProb: 0.49,
  }),
];

describe("keiWinProbForTeam", () => {
  it("resolves LAC week 1 vs ARI (not SF)", () => {
    const hit = keiWinProbForTeam(week1Lines, "LAC", 1);
    expect(hit).toEqual({
      wp: 0.78,
      opponent: "ARI",
      homeAway: "home",
      source: "kei",
    });
  });

  it("resolves SF week 1 vs LAR (Melbourne), not LAC", () => {
    const hit = keiWinProbForTeam(week1Lines, "SF", 1);
    expect(hit).toEqual({
      wp: 0.42,
      opponent: "LAR",
      homeAway: "away",
      source: "kei",
    });
  });

  it("does not collide LA / LAR with LAC", () => {
    const lar = keiWinProbForTeam(week1Lines, "LAR", 1);
    const la = keiWinProbForTeam(week1Lines, "LA", 1);
    const lac = keiWinProbForTeam(week1Lines, "LAC", 1);
    expect(lar?.opponent).toBe("SF");
    expect(la?.opponent).toBe("SF");
    expect(lac?.opponent).toBe("ARI");
    expect(lar?.wp).toBe(0.58);
    expect(lac?.wp).toBe(0.78);
  });

  it("returns null when no REG fair line exists", () => {
    expect(keiWinProbForTeam(week1Lines, "KC", 1)).toBeNull();
    expect(keiWinProbForTeam(week1Lines, "LAC", 12)).toBeNull();
  });
});

describe("overlaySurvivorPickWithKei", () => {
  it("sets display wp to KEI and preserves engine_wp", () => {
    const overlaid = overlaySurvivorPickWithKei(
      {
        team: "LAC",
        opponent: "SF", // wrong engine join — KEI must correct
        home_away: "home",
        win_rate: 0.56,
        this_week_wp: 0.56,
        favorite_wp: 0.56,
        is_favorite: true,
      },
      1,
      week1Lines,
    );
    expect(overlaid.wp_source).toBe("kei");
    expect(overlaid.this_week_wp).toBe(0.78);
    expect(overlaid.win_rate).toBe(0.78);
    expect(overlaid.favorite_wp).toBe(0.78);
    expect(overlaid.engine_wp).toBe(0.56);
    expect(overlaid.opponent).toBe("ARI");
    expect(overlaid.home_away).toBe("home");
  });

  it("falls back to engine when fair line missing", () => {
    const overlaid = overlaySurvivorPickWithKei(
      {
        team: "KC",
        opponent: "HOU",
        win_rate: 0.61,
        this_week_wp: 0.61,
      },
      1,
      week1Lines,
    );
    expect(overlaid.wp_source).toBe("engine");
    expect(overlaid.this_week_wp).toBe(0.61);
    expect(overlaid.engine_wp).toBe(0.61);
    expect(overlaid.opponent).toBe("HOU");
  });
});

describe("overlaySurvivorPlanWithKei", () => {
  it("overlays display wp and averages KEI locks only", () => {
    const plan = overlaySurvivorPlanWithKei(
      {
        locked_picks: { "1": "LAC" },
        locked_pick_count: 1,
        avg_locked_wp: 0.56,
        weeks: [
          {
            week: 1,
            locked_team: "LAC",
            locked_pick: {
              team: "LAC",
              opponent: "SF",
              win_rate: 0.56,
              this_week_wp: 0.56,
            },
            ranked_picks: [
              {
                team: "LAC",
                opponent: "SF",
                win_rate: 0.56,
                this_week_wp: 0.56,
              },
              {
                team: "SF",
                opponent: "LAC",
                win_rate: 0.44,
                this_week_wp: 0.44,
              },
            ],
          },
          {
            week: 12,
            locked_team: null,
            ranked_picks: [
              {
                team: "KC",
                opponent: "HOU",
                win_rate: 0.7,
                this_week_wp: 0.7,
              },
            ],
          },
        ],
      },
      week1Lines,
    );

    const w1 = plan.weeks![0]!;
    expect(w1.locked_pick!.this_week_wp).toBe(0.78);
    expect(w1.locked_pick!.opponent).toBe("ARI");
    expect(w1.ranked_picks![0]!.this_week_wp).toBe(0.78);
    expect(w1.ranked_picks![1]!.opponent).toBe("LAR");
    expect(w1.ranked_picks![1]!.this_week_wp).toBe(0.42);
    expect(plan.avg_locked_wp).toBe(0.78);

    // Week 12 has no KEI line — engine source, excluded from avg when locked.
    const w12 = plan.weeks![1]!;
    expect(w12.ranked_picks![0]!.wp_source).toBe("engine");
  });

  it("returns null avg when no KEI locks", () => {
    expect(
      avgLockedKeiWp(
        [
          {
            week: 12,
            locked_pick: {
              team: "KC",
              win_rate: 0.7,
              this_week_wp: 0.7,
              wp_source: "engine",
            },
          },
        ],
        { "12": "KC" },
      ),
    ).toBeNull();
  });
});

describe("sortSurvivorLeansByDisplayWp", () => {
  it("orders remaining picks by display wp descending", () => {
    const leans = sortSurvivorLeansByDisplayWp(
      [
        { team: "MID", win_rate: 0.61, this_week_wp: 0.61 },
        { team: "HIGH", win_rate: 0.5, this_week_wp: 0.78 },
        { team: "LOW", win_rate: 0.54, this_week_wp: 0.54 },
        { team: "BURN", win_rate: 0.9, this_week_wp: 0.9 },
      ],
      { burned: new Set(["BURN"]), limit: 6 },
    );
    expect(leans.map((p) => p.team)).toEqual(["HIGH", "MID", "LOW"]);
    expect(
      leans.map((p) => Math.round((p.this_week_wp ?? p.win_rate) * 100)),
    ).toEqual([78, 61, 54]);
  });
});
