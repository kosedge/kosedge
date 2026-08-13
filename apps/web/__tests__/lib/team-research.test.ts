import { describe, expect, it } from "vitest";
import {
  assignTeamPreviewWriter,
  findTeamInDirectory,
  getTeamDirectory,
  getTeamResearchSportConfig,
  listTeamResearchSportKeys,
  mlbParkFactorLabel,
  teamResearchHref,
} from "@/lib/team-research";

describe("team-research directories", () => {
  it("covers all pro hub sports", () => {
    const keys = listTeamResearchSportKeys();
    expect(keys).toEqual(
      expect.arrayContaining([
        "nfl",
        "mlb",
        "nba",
        "nhl",
        "wnba",
        "cfb",
        "ncaam",
      ]),
    );
  });

  it("has expected pro league sizes", () => {
    expect(getTeamDirectory("nfl")).toHaveLength(32);
    expect(getTeamDirectory("mlb")).toHaveLength(30);
    expect(getTeamDirectory("nba")).toHaveLength(30);
    expect(getTeamDirectory("nhl")).toHaveLength(32);
    expect(getTeamDirectory("wnba")).toHaveLength(15);
    expect(getTeamDirectory("cfb").length).toBeGreaterThan(100);
    expect(getTeamDirectory("ncaam").length).toBeGreaterThan(80);
  });

  it("resolves team slugs case-insensitively", () => {
    expect(findTeamInDirectory("mlb", "NYY")?.name).toBe("New York Yankees");
    expect(findTeamInDirectory("nba", "lal")?.code).toBe("LAL");
    expect(findTeamInDirectory("cfb", "ohio-state")?.code).toBe("OSU");
  });
});

describe("team-research writer assignment", () => {
  it("maps NFC North to Casey (matrix primary)", () => {
    const det = findTeamInDirectory("nfl", "det")!;
    const assignment = assignTeamPreviewWriter("nfl", det);
    expect(assignment.writer.id).toBe("casey-voss");
    expect(assignment.provisional).toBe(false);
  });

  it("maps NBA Northwest primary to Reese", () => {
    const den = findTeamInDirectory("nba", "den")!;
    const assignment = assignTeamPreviewWriter("nba", den);
    expect(assignment.writer.id).toBe("reese-quinn");
  });

  it("maps NHL Central primary to Morgan", () => {
    const col = findTeamInDirectory("nhl", "col")!;
    const assignment = assignTeamPreviewWriter("nhl", col);
    expect(assignment.writer.id).toBe("morgan-hale");
  });

  it("maps WNBA Western primary to Avery", () => {
    const las = findTeamInDirectory("wnba", "las")!;
    const assignment = assignTeamPreviewWriter("wnba", las);
    expect(assignment.writer.id).toBe("avery-cole");
  });

  it("maps MLB AL East to Taylor", () => {
    const bos = findTeamInDirectory("mlb", "bos")!;
    const assignment = assignTeamPreviewWriter("mlb", bos);
    expect(assignment.writer.id).toBe("taylor-brooks");
  });
});

describe("team-research sport config", () => {
  it("uses sport-appropriate coaching and depth labels", () => {
    expect(getTeamResearchSportConfig("nfl")?.coachingLabel).toContain("HC");
    expect(getTeamResearchSportConfig("mlb")?.depthLabel).toMatch(/Lineup/i);
    expect(getTeamResearchSportConfig("nba")?.statsLabels).toContain("Pace");
    expect(getTeamResearchSportConfig("nhl")?.depthLabel).toMatch(/Lines/i);
  });

  it("marks MLB park factors live and exposes factor labels", () => {
    const mlb = getTeamResearchSportConfig("mlb")!;
    expect(
      mlb.sections.find((section) => section.key === "park_factors")?.status,
    ).toBe("live");
    expect(mlbParkFactorLabel("COL")).toMatch(/1\.12/);
  });

  it("routes NFL research to existing intel URLs", () => {
    expect(teamResearchHref("nfl", "buf")).toBe("/pro/nfl/teams/BUF/overview");
    expect(teamResearchHref("mlb", "nyy")).toBe("/pro/mlb/teams/nyy");
  });
});
