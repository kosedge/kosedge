import { describe, expect, it } from "vitest";
import {
  buildProjectGameBody,
  buildSimulateBody,
  formatSpread,
  formatWinProb,
  parsePowerLadder,
  teamOptionsFromCodes,
} from "@/lib/cfb-season-engine-format";

describe("cfb-season-engine-format", () => {
  it("shapes project-game body with snake_case upstream fields", () => {
    expect(
      buildProjectGameBody({
        homeTeam: "uga",
        awayTeam: "clem",
        week: 3,
        neutralSite: true,
        nightGame: true,
      }),
    ).toEqual({
      home_team: "UGA",
      away_team: "CLEM",
      week: 3,
      season: 2026,
      neutral_site: true,
      night_game: true,
      demo: true,
    });
  });

  it("rejects same-team matchups", () => {
    expect(() =>
      buildProjectGameBody({ homeTeam: "UGA", awayTeam: "UGA" }),
    ).toThrow(/differ/);
  });

  it("caps web simulate n_sims", () => {
    expect(() => buildSimulateBody({ nSims: 200 })).toThrow(/1 and 50/);
    expect(buildSimulateBody({ nSims: 10 }).n_sims).toBe(10);
  });

  it("formats lines and parses ladder", () => {
    expect(formatSpread(-3.5)).toBe("-3.5");
    expect(formatSpread(2)).toBe("+2.0");
    expect(formatWinProb(0.612)).toBe("61.2%");
    const rows = parsePowerLadder({
      top: [
        { rank: 1, team: "ALA", power_index: 1.42, conference: "SEC" },
        { team: "UGA", power_index: 1.4 },
      ],
    });
    expect(rows).toHaveLength(2);
    expect(rows[0]?.team).toBe("ALA");
    expect(teamOptionsFromCodes(["uga", "ALA"]).map((t) => t.code)).toEqual([
      "ALA",
      "UGA",
    ]);
  });
});
