import { describe, expect, it } from "vitest";
import {
  getSportPrimaryNav,
  getSportToolNav,
  isSportNavActive,
  sportHubHref,
} from "@/lib/sport-pro-nav";
import { SPORTS } from "@/lib/sports";

describe("sport-pro-nav", () => {
  it("exposes Overview + Edge Board primary nav for every sport", () => {
    for (const sport of SPORTS) {
      const primary = getSportPrimaryNav(sport.key);
      const labels = primary.map((i) => i.label);
      expect(labels).toContain("Overview");
      expect(labels).toContain("Edge Board");
      expect(labels).toContain("KEI Lines");
      expect(labels).toContain("Edges");
      expect(labels).toContain("Teams");
      expect(labels).toContain("Power Ratings");
    }
  });

  it("surfaces Survivor / Game Boxes / Season Model on NFL primary nav", () => {
    const nflPrimary = getSportPrimaryNav("nfl").map((i) => i.label);
    expect(nflPrimary).toContain("Survivor");
    expect(nflPrimary).toContain("Game Boxes");
    expect(nflPrimary).toContain("Season Model");
  });

  it("keeps Wall Chart / Fantasy / Awards as NFL-only tools", () => {
    const nflTools = getSportToolNav("nfl").map((i) => i.label);
    expect(nflTools).toContain("Wall Chart");
    expect(nflTools).toContain("Fantasy Draft");
    expect(nflTools).toContain("Awards");
    // Season engine desks live on primary; keep them out of the overflow tools list.
    expect(nflTools).not.toContain("Season Model");
    expect(nflTools).not.toContain("Game Boxes");
    expect(nflTools).not.toContain("Survivor");

    for (const sport of SPORTS.filter((s) => s.key !== "nfl" && s.key !== "cfb")) {
      const tools = getSportToolNav(sport.key).map((i) => i.label);
      const primary = getSportPrimaryNav(sport.key).map((i) => i.label);
      expect(tools).not.toContain("Wall Chart");
      expect(tools).not.toContain("Fantasy Draft");
      expect(tools).not.toContain("Awards");
      expect(tools).not.toContain("DFS");
      expect(tools).not.toContain("Season Model");
      expect(tools).not.toContain("Survivor");
      expect(primary).not.toContain("Survivor");
      expect(primary).not.toContain("Game Boxes");
      expect(primary).not.toContain("Season Model");
    }

    // CFB season model desks are primary (not tools overflow).
    const cfbTools = getSportToolNav("cfb").map((i) => i.label);
    const cfbPrimary = getSportPrimaryNav("cfb").map((i) => i.label);
    expect(cfbTools).not.toContain("Season Model");
    expect(cfbTools).not.toContain("Project Game");
    expect(cfbPrimary).toContain("Season Model");
    expect(cfbPrimary).toContain("Project Game");
    expect(cfbPrimary).not.toContain("Survivor");
    expect(cfbPrimary).not.toContain("Game Boxes");
  });

  it("uses Tempo for college and Goalie Desk for NHL", () => {
    expect(getSportPrimaryNav("ncaam").map((i) => i.label)).toContain("Tempo");
    expect(getSportPrimaryNav("cfb").map((i) => i.label)).toContain("Tempo");
    expect(getSportPrimaryNav("cfb").map((i) => i.label)).toContain(
      "Season Model",
    );
    expect(getSportPrimaryNav("nhl").map((i) => i.label)).toContain(
      "Goalie Desk",
    );
    expect(getSportPrimaryNav("mlb").map((i) => i.label)).toContain("Run Line");
  });

  it("does not force Props into college primary nav", () => {
    expect(getSportPrimaryNav("ncaam").map((i) => i.label)).not.toContain(
      "Props",
    );
    expect(getSportPrimaryNav("cfb").map((i) => i.label)).not.toContain(
      "Props",
    );
    expect(getSportPrimaryNav("nba").map((i) => i.label)).toContain("Props");
    expect(getSportPrimaryNav("wnba").map((i) => i.label)).toContain("Props");
  });

  it("resolves hub hrefs to overview", () => {
    expect(sportHubHref("nfl")).toBe("/pro/nfl/overview");
    expect(sportHubHref("nba")).toBe("/pro/nba/overview");
  });

  it("marks overview and edge board active correctly", () => {
    expect(isSportNavActive("/pro/nba/overview", "/pro/nba/overview", "nba")).toBe(
      true,
    );
    expect(isSportNavActive("/pro/nba", "/pro/nba/overview", "nba")).toBe(true);
    expect(
      isSportNavActive("/edge-board/nba", "/edge-board/nba", "nba"),
    ).toBe(true);
    expect(
      isSportNavActive("/pro/nba/fair-lines", "/pro/nba/fair-lines", "nba"),
    ).toBe(true);
  });
});
