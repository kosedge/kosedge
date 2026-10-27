import { describe, expect, it } from "vitest";
import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  buildMatchupContext,
  type EdgeBoardMatchupContext,
} from "@/lib/edge-board-matchup-context";
import { siteClause } from "@/lib/edge-board-matchup-overview";
import { enrichNflEdgeBoardMatchupFields } from "@/lib/edge-board-matchup-enrich";
import { listCanonicalNflGames } from "@/lib/nfl-canonical-schedule";
import { deskEdgesFromFairLine } from "@/lib/nfl-edges";
import type { NflFairLineRow } from "@/lib/nfl-fair-lines";
import { normalizeFairLine } from "@/lib/nfl-fair-lines";
import { lookupNflScheduleWeek } from "@/lib/nfl-edge-board-week";
import {
  NFL_STANDARD_HFA_POINTS,
  resolveNflSiteContext,
} from "@/lib/nfl-neutral-sites-2026";

const ODDS_KICKOFF = "2026-09-13T20:00:00.000Z";
const NE_SEA_KICKOFF = "2026-09-10T00:20:00.000Z";

function regGames() {
  return listCanonicalNflGames().filter((game) => game.game_type === "REG");
}

describe("R1 D-1 site season", () => {
  it("R1 2026 REG neutral game resolves Neutral", () => {
    const site = resolveNflSiteContext({
      season: 2026,
      week: 1,
      awayAbbr: "SF",
      homeAbbr: "LAR",
    });
    expect(site.siteLabel).toBe("Neutral");
    const rows = enrichNflEdgeBoardMatchupFields(
      [
        {
          game: "San Francisco 49ers @ Los Angeles Rams",
          market: "Spread",
          awayAbbr: "SF",
          homeAbbr: "LAR",
          week: 1,
        } as EdgeBoardRow,
      ],
      { season: 2026 },
    );
    expect(rows[0]?.neutralSite).toBe(true);
  });

  it("R1 2026 home game resolves HFA", () => {
    const site = resolveNflSiteContext({
      season: 2026,
      week: 1,
      awayAbbr: "NE",
      homeAbbr: "SEA",
    });
    expect(site.siteLabel).toBe("Home");
    expect(site.hfaPoints).toBe(NFL_STANDARD_HFA_POINTS);
    const rows = enrichNflEdgeBoardMatchupFields(
      [
        {
          game: "New England Patriots @ Seattle Seahawks",
          market: "Spread",
          awayAbbr: "NE",
          homeAbbr: "SEA",
          week: 1,
        } as EdgeBoardRow,
      ],
      { season: 2026 },
    );
    expect(rows[0]?.neutralSite).toBe(false);
    expect(rows[0]?.hfaPoints).toBe(NFL_STANDARD_HFA_POINTS);
  });

  it("R1 missing or 2027 season is UNKNOWN", () => {
    expect(
      resolveNflSiteContext({
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LAR",
      }).siteLabel,
    ).toBe("UNKNOWN");
    expect(
      resolveNflSiteContext({
        season: 2027,
        week: 1,
        awayAbbr: "SF",
        homeAbbr: "LAR",
      }).siteLabel,
    ).toBe("UNKNOWN");
    const rows = enrichNflEdgeBoardMatchupFields(
      [
        {
          game: "San Francisco 49ers @ Los Angeles Rams",
          market: "Spread",
          awayAbbr: "SF",
          homeAbbr: "LAR",
          week: 1,
        } as EdgeBoardRow,
      ],
      { season: null },
    );
    expect(rows[0]?.neutralSite).toBe(false);
    expect(rows[0]?.hfaPoints == null).toBe(true);
  });
});

describe("R2 D-2 raw season", () => {
  const raw = {
    game_id: "odds-uuid",
    week: 1,
    away_abbr: "NE",
    home_abbr: "SEA",
    start_time: ODDS_KICKOFF,
    season_type: "REG",
  };

  it("R2 present raw.season is used", () => {
    const line = normalizeFairLine({ ...raw, season: 2026 }, 2026);
    expect(line.startTime).toBe(NE_SEA_KICKOFF);
    expect(line.season).toBe(2026);
  });

  it("R2 absent, null, or 0 raw.season uses the request season", () => {
    expect(normalizeFairLine(raw, 2026).startTime).toBe(NE_SEA_KICKOFF);
    expect(normalizeFairLine({ ...raw, season: null }, 2026).startTime).toBe(
      NE_SEA_KICKOFF,
    );
    expect(normalizeFairLine({ ...raw, season: 0 }, 2026).startTime).toBe(
      NE_SEA_KICKOFF,
    );
  });

  it("R2 a present different raw.season is not overridden", () => {
    const line = normalizeFairLine({ ...raw, season: 2027 }, 2026);
    expect(line.season).toBe(2027);
    expect(line.startTime).toBe(ODDS_KICKOFF);
  });
});

describe("R3 D-3 kickoff season", () => {
  function row(season: number): NflFairLineRow {
    return {
      marketJoined: true,
      gameId: "odds-uuid",
      season,
      week: 1,
      seasonType: "REG",
      awayAbbr: "NE",
      homeAbbr: "SEA",
      startTime: ODDS_KICKOFF,
      gameDate: null,
      mlEdgeProb: 1,
      fairHomeMl: null,
      fairAwayMl: null,
      marketHomeMl: null,
      marketAwayMl: null,
    } as NflFairLineRow;
  }

  it("R3 canonical kickoff with payload season and without it", () => {
    const withSeason = deskEdgesFromFairLine(row(2026), {
      minProbEdge: 0,
      minLineEdge: 0,
      requestSeason: 2026,
    });
    const withoutSeason = deskEdgesFromFairLine(row(0), {
      minProbEdge: 0,
      minLineEdge: 0,
      requestSeason: 2026,
    });
    expect(withSeason[0]?.kickoff).toBe(NE_SEA_KICKOFF);
    expect(withoutSeason[0]?.kickoff).toBe(NE_SEA_KICKOFF);
  });
});

describe("R5 CHECK-140", () => {
  it("R5 a collision game with week omitted keeps the pack week", () => {
    const games = regGames();
    const directed = games.find((game) =>
      games.some(
        (other) =>
          other.away_team_id === game.home_team_id &&
          other.home_team_id === game.away_team_id &&
          other.week !== game.week,
      ),
    );
    expect(directed).toBeTruthy();
    const rows = enrichNflEdgeBoardMatchupFields(
      [
        {
          game: `${directed!.away_team_id} @ ${directed!.home_team_id}`,
          market: "Spread",
          awayAbbr: directed!.away_team_id,
          homeAbbr: directed!.home_team_id,
        } as EdgeBoardRow,
      ],
      { season: 2026 },
    );
    expect(rows[0]?.week).toBe(directed!.week);
  });

  it("R5 non-identifiable input is null or UNKNOWN", () => {
    expect(lookupNflScheduleWeek({ awayAbbr: "", homeAbbr: "" })).toBeNull();
    expect(
      resolveNflSiteContext({
        season: null,
        week: null,
        awayAbbr: "",
        homeAbbr: "",
      }).siteLabel,
    ).toBe("UNKNOWN");
    const rows = enrichNflEdgeBoardMatchupFields(
      [{ game: "", market: "Spread" } as EdgeBoardRow],
      { season: null },
    );
    expect(rows[0]?.week == null).toBe(true);
    expect(rows[0]?.hfaPoints == null).toBe(true);
  });
});

describe("buildMatchupContext season propagation", () => {
  it("C1 R1 REG neutral with season resolves Neutral", () => {
    const ctx = buildMatchupContext({
      awayName: "San Francisco 49ers",
      homeName: "Los Angeles Rams",
      awayAbbr: "SF",
      homeAbbr: "LAR",
      week: 1,
      season: 2026,
      seasonType: "REG",
    });
    expect(ctx.siteLabel).toBe("Neutral");
    expect(ctx.isNeutral).toBe(true);
  });

  it("C2 R1 neutral game with season omitted is UNKNOWN", () => {
    const ctx = buildMatchupContext({
      awayName: "San Francisco 49ers",
      homeName: "Los Angeles Rams",
      awayAbbr: "SF",
      homeAbbr: "LAR",
      week: 1,
      seasonType: "REG",
    });
    expect(ctx.siteLabel).toBe("UNKNOWN");
    expect(ctx.hfaPoints).toBeNull();
  });

  it("C3 R1 home game with season resolves Home", () => {
    const ctx = buildMatchupContext({
      awayName: "New England Patriots",
      homeName: "Seattle Seahawks",
      awayAbbr: "NE",
      homeAbbr: "SEA",
      week: 1,
      season: 2026,
      seasonType: "REG",
    });
    expect(ctx.siteLabel).toBe("Home");
    expect(ctx.hfaPoints).toBe(NFL_STANDARD_HFA_POINTS);
  });

  it("C4 R1 foreign season is UNKNOWN", () => {
    const ctx = buildMatchupContext({
      awayName: "San Francisco 49ers",
      homeName: "Los Angeles Rams",
      awayAbbr: "SF",
      homeAbbr: "LAR",
      week: 1,
      season: 2027,
      seasonType: "REG",
    });
    expect(ctx.siteLabel).toBe("UNKNOWN");
  });

  it("C5 enrich path with options.season sets neutralSite", () => {
    const rows = enrichNflEdgeBoardMatchupFields(
      [
        {
          game: "San Francisco 49ers @ Los Angeles Rams",
          market: "Spread",
          awayAbbr: "SF",
          homeAbbr: "LAR",
          week: 1,
        } as EdgeBoardRow,
      ],
      { season: 2026 },
    );
    expect(rows[0]?.neutralSite).toBe(true);
  });
});

describe("siteClause HFA display", () => {
  it("C6 known HFA siteClause formats the standard HFA", () => {
    const home = buildMatchupContext({
      awayName: "New England Patriots",
      homeName: "Seattle Seahawks",
      awayAbbr: "NE",
      homeAbbr: "SEA",
      week: 1,
      season: 2026,
      seasonType: "REG",
    });
    const ctx: EdgeBoardMatchupContext = { ...home, isNeutral: true };
    const clause = siteClause(ctx);
    expect(clause).toContain(NFL_STANDARD_HFA_POINTS.toFixed(2));
  });

  it("C7 null HFA siteClause omits the numeric phrase", () => {
    const built = buildMatchupContext({
      awayName: "San Francisco 49ers",
      homeName: "Los Angeles Rams",
      awayAbbr: "SF",
      homeAbbr: "LAR",
      week: 1,
      season: 2026,
      seasonType: "REG",
    });
    const ctx: EdgeBoardMatchupContext = {
      ...built,
      isNeutral: true,
      hfaPoints: null,
    };
    const clause = siteClause(ctx);
    expect(clause).toBeNull();
    expect(
      clause === null ||
        (typeof clause === "string" &&
          !clause.includes("0.0") &&
          !clause.includes("NaN") &&
          !clause.includes("null") &&
          !clause.includes("undefined")),
    ).toBe(true);
  });

  it("C8 enrich with season omitted keeps hfaPoints unset", () => {
    const rows = enrichNflEdgeBoardMatchupFields([
      {
        game: "San Francisco 49ers @ Los Angeles Rams",
        market: "Spread",
        awayAbbr: "SF",
        homeAbbr: "LAR",
        week: 1,
      } as EdgeBoardRow,
    ]);
    expect(rows[0]?.hfaPoints == null).toBe(true);
  });
});
