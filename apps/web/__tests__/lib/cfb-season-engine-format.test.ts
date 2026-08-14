import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  americanOddsFromWinProb,
  buildProjectGameBody,
  buildSimulateBody,
  formatAmericanOdds,
  formatFavoriteSpread,
  formatProjectedScoreLine,
  formatSpread,
  formatWinProb,
  formatWinProbWithMl,
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

  it("accepts Week 0 project-game bodies", () => {
    expect(
      buildProjectGameBody({
        homeTeam: "TCU",
        awayTeam: "UNC",
        week: 0,
      }),
    ).toEqual({
      home_team: "TCU",
      away_team: "UNC",
      week: 0,
      season: 2026,
      neutral_site: false,
      night_game: false,
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

  it("formats favorite spread wording from home-centric line", () => {
    expect(formatFavoriteSpread(-5.1, "OSU", "MICH")).toBe("OSU -5.1");
    expect(formatFavoriteSpread(3.0, "UGA", "CLEM")).toBe("CLEM -3.0");
    expect(formatFavoriteSpread(0.02, "ALA", "LSU")).toBe("Pick'em");
    expect(formatFavoriteSpread(null, "ALA", "LSU")).toBe("—");
  });

  it("converts win probability to American moneyline", () => {
    expect(americanOddsFromWinProb(0.5)).toBe(-100);
    expect(americanOddsFromWinProb(0.596)).toBe(-148);
    expect(americanOddsFromWinProb(0.404)).toBe(148);
    expect(americanOddsFromWinProb(0.75)).toBe(-300);
    expect(americanOddsFromWinProb(0.25)).toBe(300);
    expect(americanOddsFromWinProb(null)).toBeNull();
    expect(formatAmericanOdds(-148)).toBe("-148");
    expect(formatAmericanOdds(148)).toBe("+148");
    expect(formatWinProbWithMl(0.596)).toBe("59.6% (-148)");
    expect(formatProjectedScoreLine(31.9, 36.9)).toBe("31.9 – 36.9");
  });
});

describe("CFB model page honesty", () => {
  it("interpolates roster depth/portal instead of printing brace placeholders", () => {
    const src = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/cfb/model/page.tsx"),
      "utf8",
    );
    expect(src).toContain("` · depth ${status.depth_source}`");
    expect(src).toContain("` · portal ${status.portal_source}`");
    expect(src).not.toContain("` · depth {status.depth_source}`");
  });
});
