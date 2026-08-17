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
      expect(labels).toContain("Teams");
      const edgeBoard = primary.find((i) => i.label === "Edge Board");
      expect(edgeBoard?.emphasis).toBe("green");
      if (sport.key === "cfb") {
        expect(labels).toContain("Slate");
        expect(labels).toContain("Model");
        expect(labels).toContain("Project Game");
        expect(labels).toContain("Projections");
        expect(labels).toContain("Previews");
        expect(labels).not.toContain("Edges");
        expect(labels).not.toContain("Fair Lines");
        expect(labels).not.toContain("KEI Lines");
      } else {
        expect(labels).toContain("Edges");
        expect(labels).toContain("Power Ratings");
        if (sport.key !== "nfl") {
          if (sport.key === "nhl") {
            expect(labels).toContain("Fair Lines");
            expect(labels).not.toContain("KEI Lines");
          } else {
            expect(labels).toContain("KEI Lines");
          }
        }
      }
    }
  });

  it("locks NFL primary nav order and demotes KEI / model / boxes / previews", () => {
    const nflPrimary = getSportPrimaryNav("nfl");
    const labels = nflPrimary.map((i) => i.label);
    expect(labels).toEqual([
      "Overview",
      "Edge Board",
      "Weekly Slate",
      "Edges",
      "Survivor",
      "Fantasy",
      "Power Ratings",
      "Camp Desk",
      "Teams",
    ]);
    // Demoted from primary — live in Overview body / More tools.
    expect(labels).not.toContain("KEI Lines");
    expect(labels).not.toContain("Season Model");
    expect(labels).not.toContain("Game Boxes");
    expect(labels).not.toContain("Team Previews");
    // Unfinished desks stay off primary until live.
    expect(labels).not.toContain("Props");
    expect(labels).not.toContain("DFS");
    expect(labels).not.toContain("Awards");
    expect(labels).not.toContain("Player Previews");
    expect(labels).not.toContain("Sport Tracking");
    const fantasy = nflPrimary.find((i) => i.label === "Fantasy");
    expect(fantasy?.href).toBe("/pro/nfl/fantasy");
  });

  it("keeps Wall Chart as NFL-only tool; Fantasy on primary; demoted desks in tools", () => {
    const nflTools = getSportToolNav("nfl").map((i) => i.label);
    expect(nflTools).toContain("Wall Chart");
    expect(nflTools).toContain("Weekly Fantasy");
    expect(nflTools).toContain("KEI Lines");
    expect(nflTools).toContain("Season Model");
    expect(nflTools).toContain("Game Boxes");
    expect(nflTools).toContain("Team Previews");
    // Fantasy Draft Desk is primary — not duplicated in tools overflow.
    expect(nflTools).not.toContain("Draft Desk");
    expect(nflTools).not.toContain("Fantasy");
    expect(nflTools).not.toContain("Survivor");
    // Camp Desk is primary — not duplicated in tools.
    expect(nflTools).not.toContain("Camp");
    expect(nflTools).not.toContain("Camp Desk");
    // Unfinished surfaces demoted until live (no tools chrome that looks ready).
    expect(nflTools).not.toContain("Awards");
    expect(nflTools).not.toContain("DFS");
    expect(nflTools).not.toContain("Player Previews");
    expect(nflTools).not.toContain("Props");
    expect(nflTools).not.toContain("Sport Tracking");

    for (const sport of SPORTS.filter((s) => s.key !== "nfl" && s.key !== "cfb")) {
      const tools = getSportToolNav(sport.key).map((i) => i.label);
      const primary = getSportPrimaryNav(sport.key).map((i) => i.label);
      expect(tools).not.toContain("Wall Chart");
      expect(tools).not.toContain("Draft Desk");
      expect(tools).not.toContain("Awards");
      expect(tools).not.toContain("DFS");
      expect(tools).not.toContain("Season Model");
      expect(tools).not.toContain("Survivor");
      expect(primary).not.toContain("Survivor");
      expect(primary).not.toContain("Game Boxes");
      expect(primary).not.toContain("Fantasy");
      expect(primary).not.toContain("Season Model");
    }

    // CFB season model desks are primary (not tools overflow).
    const cfbTools = getSportToolNav("cfb").map((i) => i.label);
    const cfbPrimary = getSportPrimaryNav("cfb").map((i) => i.label);
    expect(cfbTools).not.toContain("Season Model");
    expect(cfbTools).not.toContain("Project Game");
    expect(cfbPrimary).toContain("Model");
    expect(cfbPrimary).toContain("Project Game");
    expect(cfbPrimary).toContain("Slate");
    expect(cfbPrimary).toContain("Projections");
    expect(cfbPrimary).toContain("Teams");
    expect(cfbPrimary).toContain("Previews");
    expect(cfbPrimary).toContain("Futures");
    expect(cfbPrimary).not.toContain("Fair Lines");
    expect(cfbPrimary).not.toContain("Edges");
    expect(cfbPrimary).not.toContain("KEI Lines");
    expect(cfbTools).toContain("KEI Lines");
    expect(cfbTools).toContain("Conferences");
    expect(cfbTools).not.toContain("KEI (not shipped)");
    expect(cfbTools).not.toContain("KEI Projections");
    expect(cfbPrimary).not.toContain("Survivor");
    expect(cfbPrimary).not.toContain("Game Boxes");
    expect(cfbPrimary).not.toContain("Fantasy");
  });

  it("uses Tempo for college and Goalie Desk for NHL", () => {
    expect(getSportPrimaryNav("ncaam").map((i) => i.label)).toContain("Tempo");
    expect(getSportToolNav("cfb").map((i) => i.label)).toContain("Conferences");
    expect(getSportPrimaryNav("cfb").map((i) => i.label)).toContain("Model");
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

  it("keeps Fantasy nav active across Draft Desk subpages", () => {
    const href = "/pro/nfl/fantasy";
    expect(isSportNavActive("/pro/nfl/fantasy", href, "nfl")).toBe(true);
    expect(isSportNavActive("/pro/nfl/fantasy/builder", href, "nfl")).toBe(
      true,
    );
    expect(isSportNavActive("/pro/nfl/fantasy/mock", href, "nfl")).toBe(true);
    expect(
      isSportNavActive("/pro/nfl/fantasy/player/abc", href, "nfl"),
    ).toBe(true);
    expect(isSportNavActive("/pro/nfl/fantasy/guillotine", href, "nfl")).toBe(
      true,
    );
    expect(isSportNavActive("/pro/nfl/fantasy/sleepers", href, "nfl")).toBe(
      true,
    );
    expect(isSportNavActive("/pro/nfl/weekly-fantasy", href, "nfl")).toBe(
      false,
    );
  });
});
