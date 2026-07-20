import { describe, expect, it } from "vitest";
import {
  buildSportOverviewContent,
  buildSportOverviewSections,
  hasArticleData,
} from "@/lib/pro-sport-ia";
import { supportsPropsFantasy } from "@/lib/sports";
import type { LegacyEdgeBoardRow } from "@/components/EdgeBoard";

function buildRow(overrides: Partial<LegacyEdgeBoardRow> = {}): LegacyEdgeBoardRow {
  return {
    id: "row-1",
    time: "8:00 PM ET",
    teamA: { name: "Away Team", site: "Away" },
    teamB: { name: "Home Team", site: "Home" },
    openOU: { top: { label: "o145.5", juice: "-110" }, bottom: { label: "u145.5", juice: "-110" } },
    openLine: { top: { label: "+2.5", juice: "-110" }, bottom: { label: "-2.5", juice: "-110" } },
    bestLine: { top: { label: "+2.0", juice: "-108" }, bottom: { label: "-2.0", juice: "-112" } },
    bestOU: { top: { label: "o146.5", juice: "-110" }, bottom: { label: "u146.5", juice: "-110" } },
    ...overrides,
  };
}

describe("pro sport IA", () => {
  it("marks college sports as props-disabled", () => {
    expect(supportsPropsFantasy("ncaam")).toBe(false);
    expect(supportsPropsFantasy("cfb")).toBe(false);
    expect(supportsPropsFantasy("nfl")).toBe(true);
  });

  it("builds active props links for pro sports", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    const propsSection = sections.find((section) => section.title === content.sectionTitles.props);
    expect(propsSection?.links.some((link) => link.href === "/pro/nfl/props")).toBe(true);
    expect(propsSection?.links.every((link) => link.status !== "placeholder")).toBe(true);
  });

  it("points NFL fair lines to the dedicated board", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    const marketSection = sections.find((section) => section.title === content.sectionTitles.market);
    const fairLines = marketSection?.links.find((link) => link.label === "Fair lines");
    expect(fairLines?.href).toBe("/pro/nfl/fair-lines");
    expect(fairLines?.status).toBe("active");
  });

  it("adds NFL-only team intel section with active links", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });

    const intelSection = sections.find((section) => section.title === "Team Intel");
    expect(intelSection).toBeDefined();
    expect(intelSection?.links.map((link) => link.label)).toEqual([
      "Projections hub",
      "Fair lines board",
      "Props board",
      "Fantasy draft board",
      "MVP & OPOY race",
      "2026 NFL wall chart",
      "Team intel hub",
      "League stats",
      "League standings",
      "Depth charts",
      "Injuries",
    ]);
    expect(intelSection?.links.map((link) => link.href)).toEqual([
      "/pro/nfl/projections",
      "/pro/nfl/fair-lines",
      "/pro/nfl/props",
      "/pro/nfl/fantasy",
      "/pro/nfl/awards",
      "/wall-chart/nfl-2026",
      "/pro/nfl/teams",
      "/pro/nfl/stats",
      "/pro/nfl/standings",
      "/pro/nfl/depth-charts",
      "/pro/nfl/injuries",
    ]);
    expect(intelSection?.links.every((link) => link.status === "active")).toBe(true);
    expect(intelSection?.links.every((link) => link.premium)).toBe(true);
  });

  it("does not add team intel section for non-NFL sports", () => {
    const content = buildSportOverviewContent("cfb", "College Football");
    const sections = buildSportOverviewSections({
      sportKey: "cfb",
      base: "/pro/cfb",
      edgeBoardHref: "/edge-board/cfb",
      content,
    });

    expect(sections.some((section) => section.title === "Team Intel")).toBe(false);
  });

  it("builds placeholder props links for college sports", () => {
    const content = buildSportOverviewContent("cfb", "College Football");
    const sections = buildSportOverviewSections({
      sportKey: "cfb",
      base: "/pro/cfb",
      edgeBoardHref: "/edge-board/cfb",
      content,
    });
    const propsSection = sections.find((section) => section.title === content.sectionTitles.props);
    expect(propsSection?.links.length).toBeGreaterThan(0);
    expect(propsSection?.links.every((link) => !link.href)).toBe(true);
    expect(propsSection?.links.every((link) => link.status === "placeholder")).toBe(true);
  });

  it("requires line and total labels for article-ready cards", () => {
    expect(hasArticleData(buildRow())).toBe(true);
    expect(
      hasArticleData(
        buildRow({
          bestOU: { top: { label: "—", juice: "" }, bottom: { label: "—", juice: "" } },
        }),
      ),
    ).toBe(false);
  });
});
