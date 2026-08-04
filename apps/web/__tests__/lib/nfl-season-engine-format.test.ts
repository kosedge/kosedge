import { describe, expect, it } from "vitest";
import {
  buildGameBoxesQuery,
  buildStarOutInjuryPath,
  buildSurvivorBody,
  formatPct,
  formatRange,
  matchupsFromWallChart,
  normalizeNflTeamCode,
  parseAlreadyUsedTeams,
  primaryStatsForPosition,
  rankSurvivorPicks,
  starOutOptionsForMatchup,
} from "@/lib/nfl-season-engine-format";
import wallChart2026 from "@/lib/nfl-wall-chart-2026.schedule.json";

describe("nfl-season-engine-format", () => {
  it("normalizes team aliases and parses used lists", () => {
    expect(normalizeNflTeamCode("lar")).toBe("LA");
    expect(normalizeNflTeamCode("WSH")).toBe("WAS");
    expect(normalizeNflTeamCode("zzz")).toBeNull();
    expect(parseAlreadyUsedTeams("KC, buf; LAR LAR")).toEqual([
      "KC",
      "BUF",
      "LA",
    ]);
  });

  it("shapes game-boxes query with clamps and validation", () => {
    expect(
      buildGameBoxesQuery({
        homeTeam: "kc",
        awayTeam: "buf",
        week: 99,
        nReplicates: 10,
      }),
    ).toMatchObject({
      home_team: "KC",
      away_team: "BUF",
      week: 22,
      n_replicates: 50,
    });
    expect(() =>
      buildGameBoxesQuery({ homeTeam: "KC", awayTeam: "KC" }),
    ).toThrow(/differ/);
  });

  it("shapes survivor body and injury path helpers", () => {
    expect(
      buildSurvivorBody({
        week: 5,
        alreadyUsed: "KC,BUF",
        nSims: 9999,
        topN: 8,
      }),
    ).toMatchObject({
      week: 5,
      already_used: ["KC", "BUF"],
      n_sims: 500,
      top_n: 8,
      include_diagnostics: true,
    });
    expect(
      buildStarOutInjuryPath({
        team: "SF",
        playerName: "Christian McCaffrey",
        week: 4,
      }),
    ).toEqual({
      team: "SF",
      status: "out",
      week_start: 4,
      week_end: 4,
      player_name: "Christian McCaffrey",
    });
    expect(starOutOptionsForMatchup("SF", "KC").map((s) => s.playerName)).toEqual(
      expect.arrayContaining(["Christian McCaffrey", "Patrick Mahomes"]),
    );
  });

  it("expands 2026 wall-chart into 272 unique matchups with byes", () => {
    const matchups = matchupsFromWallChart(
      wallChart2026 as Record<string, Record<string, string>>,
      { season: 2026 },
    );
    expect(matchups).toHaveLength(272);
    expect(matchups.some((m) => m.awayTeam === "ARI" && m.homeTeam === "LAC" && m.week === 1)).toBe(
      true,
    );
    expect(matchups.some((m) => m.awayTeam === "SF" && m.homeTeam === "LA" && m.week === 1)).toBe(
      true,
    );
    const week5Teams = new Set(
      matchups
        .filter((m) => m.week === 5)
        .flatMap((m) => [m.homeTeam, m.awayTeam]),
    );
    expect(week5Teams.has("KC")).toBe(false);
    expect(week5Teams.has("CAR")).toBe(false);
  });

  it("ranks picks and formats display helpers", () => {
    const ranked = rankSurvivorPicks([
      { team: "A", pick_now_score: 0.2 },
      { team: "B", pick_now_score: 0.5 },
    ]);
    expect(ranked.map((r) => r.team)).toEqual(["B", "A"]);
    expect(ranked[0]?.rank).toBe(1);
    expect(primaryStatsForPosition("QB")).toContain("pass_yards");
    expect(formatPct(0.641)).toBe("64.1%");
    expect(
      formatRange({ mean: 10, std: 1, p10: 5, p50: 10, p90: 15 }),
    ).toBe("5–15");
    expect(
      formatRange({ mean: 10.2, std: 1, p10: 5.2, p50: 10.2, p90: 15.8 }),
    ).toBe("5.2–15.8");
  });
});
