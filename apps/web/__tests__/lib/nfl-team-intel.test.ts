import { describe, expect, it } from "vitest";
import {
  buildTrendSnippets,
  buildTeamIntelHref,
  filterTeamDirectory,
  parseTeamIntelFilters,
  resolveTeamCode,
} from "@/lib/nfl-team-intel";

describe("nfl-team-intel helpers", () => {
  it("builds team intel links with season/week filters", () => {
    expect(
      buildTeamIntelHref("BUF", "overview", { season: 2025, week: 12 }),
    ).toBe("/pro/nfl/teams/BUF/overview?season=2025&week=12");
    expect(buildTeamIntelHref("BUF", "injuries")).toBe(
      "/pro/nfl/teams/BUF/injuries",
    );
  });

  it("parses valid filters and ignores invalid values", () => {
    const parsed = parseTeamIntelFilters({
      season: "2025",
      week: "12",
      conference: "AFC",
      division: "East",
      q: "Bills",
    });
    expect(parsed).toEqual({
      season: 2025,
      week: 12,
      conference: "AFC",
      division: "East",
      query: "Bills",
    });

    const invalid = parseTeamIntelFilters({
      season: "1901",
      week: "99",
      conference: "x",
      division: "y",
    });
    expect(invalid.season).toBeUndefined();
    expect(invalid.week).toBeUndefined();
    expect(invalid.conference).toBeUndefined();
    expect(invalid.division).toBeUndefined();
  });

  it("resolves team code to valid fallback", () => {
    expect(resolveTeamCode("mia", ["BUF", "MIA", "NE"])).toBe("MIA");
    expect(resolveTeamCode("zzz", ["BUF", "MIA", "NE"])).toBe("BUF");
    expect(resolveTeamCode(undefined, [])).toBe("BUF");
  });

  it("filters directory by conference/division/search", () => {
    const filtered = filterTeamDirectory({
      conference: "AFC",
      division: "East",
      query: "new",
    });
    expect(filtered.map((team) => team.code)).toEqual(["NE", "NYJ"]);
  });

  it("formats trend snippet numerics to 3 decimals", () => {
    const snippets = buildTrendSnippets({
      pass_rate: 0.58123,
      red_zone_td_rate: 0.61456,
      epa_per_play_offense: 0.12349,
      epa_per_play_defense_allowed: -0.04321,
    });
    expect(snippets[0]).toContain("58.123%");
    expect(snippets[0]).toContain("61.456%");
    expect(snippets[1]).toContain("+0.123");
    expect(snippets[1]).toContain("-0.043");
  });
});
