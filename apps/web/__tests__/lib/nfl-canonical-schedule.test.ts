import { describe, expect, it } from "vitest";
import {
  NFL_REG_GAME_COUNT,
  NFL_TEAM_COUNT,
  NFL_WEEK1_KICKOFF_ANCHORS,
  canonicalKickoffForMatchup,
  formatKickoffEt,
  listCanonicalNflGames,
  lookupCanonicalNflGame,
  week1AuditRows,
} from "@/lib/nfl-canonical-schedule";
import { resolveNflKickoffIso } from "@/lib/nfl-schedule-kickoff";
import {
  edgesMayShowPropRows,
  nflPropsSurfaceState,
} from "@/lib/nfl-props-surface";
import { NFL_WEEKLY_PROPS_LIVE } from "@/lib/nfl-weekly-props-live";
import { matchupsFromWallChart } from "@/lib/nfl-season-engine-format";
import { getWallChartSchedule } from "@/lib/nfl-wall-chart-2026";
import { NFL_CANONICAL_TEAMS } from "@/lib/nfl-canonical-teams";

describe("canonical NFL schedule", () => {
  it("has 32 teams and 272 REG games", () => {
    const games = listCanonicalNflGames();
    expect(games).toHaveLength(NFL_REG_GAME_COUNT);
    const teams = new Set(
      games.flatMap((g) => [g.away_team_id, g.home_team_id]),
    );
    expect(teams.size).toBe(NFL_TEAM_COUNT);
    for (const t of NFL_CANONICAL_TEAMS) {
      expect(teams.has(t)).toBe(true);
    }
  });

  it("locks Week 1 primetime / Melbourne anchors", () => {
    for (const anchor of NFL_WEEK1_KICKOFF_ANCHORS) {
      const game = lookupCanonicalNflGame({ gameId: anchor.game_id });
      expect(game?.kickoff_utc).toBe(anchor.kickoff_utc);
      expect(formatKickoffEt(game?.kickoff_utc)).toBe(anchor.kickoff_et);
      expect(game?.venue).toBe(anchor.venue);
    }
  });

  it("does not default Week 1 to 4:00 PM ET", () => {
    const w1 = listCanonicalNflGames().filter((g) => g.week === 1);
    expect(w1).toHaveLength(16);
    for (const game of w1) {
      expect(game.kickoff_utc).toBeTruthy();
      expect(formatKickoffEt(game.kickoff_utc)).not.toBe("4:00 PM ET");
    }
  });

  it("audits Week 1 clocks against official anchors", () => {
    const rows = week1AuditRows();
    expect(rows).toHaveLength(16);
    expect(rows.every((r) => r.match === "Y")).toBe(true);
    const ne = rows.find((r) => r.game_id === "2026-W01-NE@SEA");
    const sf = rows.find((r) => r.game_id === "2026-W01-SF@LAR");
    expect(ne?.kosedge_kickoff_et).toBe("8:20 PM ET");
    expect(sf?.kosedge_kickoff_et).toBe("8:35 PM ET");
  });

  it("lets canonical kickoff beat a fake 4pm odds commence", () => {
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        week: 1,
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
        commenceTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-10T00:20:00.000Z");
    expect(
      resolveNflKickoffIso({
        gameId: "odds-uuid",
        awayAbbr: "NE",
        homeAbbr: "SEA",
        startTime: "2026-09-13T20:00:00.000Z",
      }),
    ).toBe("2026-09-10T00:20:00.000Z");
  });

  it("stamps wall-chart matchups with kickoff_utc", () => {
    const rows = matchupsFromWallChart(getWallChartSchedule());
    expect(rows).toHaveLength(NFL_REG_GAME_COUNT);
    const ne = rows.find(
      (r) => r.awayTeam === "NE" && r.homeTeam === "SEA" && r.week === 1,
    );
    expect(ne?.startTime).toBe("2026-09-10T00:20:00.000Z");
    const scheduled = rows.filter((r) => r.week === 1);
    expect(scheduled.every((r) => r.startTime)).toBe(true);
  });

  it("treats flex TBD as honest null, not an odds fallback", () => {
    const hit = canonicalKickoffForMatchup({
      week: 18,
      awayAbbr: "MIA",
      homeAbbr: "NE",
    });
    expect(hit.found).toBe(true);
    expect(hit.kickoffUtc).toBeNull();
    expect(
      resolveNflKickoffIso({
        gameId: "x",
        week: 18,
        awayAbbr: "MIA",
        homeAbbr: "NE",
        startTime: "2027-01-10T20:00:00.000Z",
      }),
    ).toBeNull();
  });
});

describe("Props ↔ Edges surface", () => {
  it("keeps Edges prop rows off when Props is empty or gated", () => {
    expect(
      edgesMayShowPropRows(
        nflPropsSurfaceState({
          rows: [],
          diagnostics: { notLive: true, marketJoinedCount: 0 },
        }),
      ),
    ).toBe(false);
    expect(
      edgesMayShowPropRows(
        nflPropsSurfaceState({
          rows: [],
          diagnostics: {
            notLive: !NFL_WEEKLY_PROPS_LIVE,
            marketJoinedCount: 0,
          },
        }),
      ),
    ).toBe(false);
    expect(
      edgesMayShowPropRows(
        nflPropsSurfaceState({
          rows: [{ marketJoined: true }],
          diagnostics: { notLive: false, marketJoinedCount: 1 },
        }),
      ),
    ).toBe(NFL_WEEKLY_PROPS_LIVE);
  });
});
