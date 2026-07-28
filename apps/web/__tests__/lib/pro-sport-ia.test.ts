import { describe, expect, it } from "vitest";
import {
  buildSportOverviewContent,
  buildSportOverviewSections,
  hasArticleData,
} from "@/lib/pro-sport-ia";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import { SPORTS, supportsPropsFantasy } from "@/lib/sports";
import type { LegacyEdgeBoardRow } from "@/components/EdgeBoard";

function buildRow(
  overrides: Partial<LegacyEdgeBoardRow> = {},
): LegacyEdgeBoardRow {
  return {
    id: "row-1",
    time: "8:00 PM ET",
    teamA: { name: "Away Team", site: "Away" },
    teamB: { name: "Home Team", site: "Home" },
    openOU: {
      top: { label: "o145.5", juice: "-110" },
      bottom: { label: "u145.5", juice: "-110" },
    },
    openLine: {
      top: { label: "+2.5", juice: "-110" },
      bottom: { label: "-2.5", juice: "-110" },
    },
    bestLine: {
      top: { label: "+2.0", juice: "-108" },
      bottom: { label: "-2.0", juice: "-112" },
    },
    bestOU: {
      top: { label: "o146.5", juice: "-110" },
      bottom: { label: "u146.5", juice: "-110" },
    },
    ...overrides,
  };
}

describe("pro sport IA", () => {
  it("marks college sports as props-disabled", () => {
    expect(supportsPropsFantasy("ncaam")).toBe(false);
    expect(supportsPropsFantasy("cfb")).toBe(false);
    expect(supportsPropsFantasy("nfl")).toBe(true);
  });

  it("builds active props links for NFL", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    const propsSection = sections.find(
      (section) => section.title === content.sectionTitles.props,
    );
    expect(
      propsSection?.links.some((link) => link.href === "/pro/nfl/props"),
    ).toBe(true);
    expect(
      propsSection?.links.every((link) => link.status !== "placeholder"),
    ).toBe(true);
  });

  it("points NFL betting desk path KEI Lines → Edges → Props", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    expect(content.sectionTitles.market).toBe("Betting Desk");
    const marketSection = sections.find(
      (section) => section.title === content.sectionTitles.market,
    );
    expect(marketSection?.subtitle).toContain("KEI Lines → Edges → Props");
    const labels = marketSection?.links.map((link) => link.label) ?? [];
    expect(labels.slice(0, 3)).toEqual(["KEI Lines", "Edges", "Props"]);
    expect(
      marketSection?.links.find((link) => link.label === "KEI Lines")?.href,
    ).toBe("/pro/nfl/fair-lines");
    expect(
      marketSection?.links.find((link) => link.label === "Edges")?.href,
    ).toBe("/pro/nfl/edges");
    expect(
      marketSection?.links.find((link) => link.label === "Props")?.href,
    ).toBe("/pro/nfl/props");
  });

  it("points MLB betting desk path Fair Lines → Edges → Run Line", () => {
    const desk = getSportDeskConfig("mlb");
    expect(desk.pathLabel).toBe("Fair Lines → Edges → Run Line");
    expect(desk.cards.map((c) => c.title)).toEqual([
      "Fair Lines",
      "Edges",
      "Run Line",
    ]);
    expect(desk.cards[0]?.href).toBe("/pro/mlb/fair-lines");
    expect(desk.cards[1]?.href).toBe("/pro/mlb/edges");
    expect(desk.cards[2]?.href).toContain("focus=run-line");

    const content = buildSportOverviewContent("mlb", "MLB");
    const sections = buildSportOverviewSections({
      sportKey: "mlb",
      base: "/pro/mlb",
      edgeBoardHref: "/edge-board/mlb",
      content,
    });
    const marketSection = sections.find(
      (section) => section.title === content.sectionTitles.market,
    );
    expect(marketSection?.subtitle).toContain("Fair Lines → Edges → Run Line");
    const labels = marketSection?.links.map((link) => link.label) ?? [];
    expect(labels.slice(0, 3)).toEqual(["Fair Lines", "Edges", "Run Line"]);
  });

  it("adds NFL team intel section with active links", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });

    const intelSection = sections.find(
      (section) => section.title === "Team Intel",
    );
    expect(intelSection).toBeDefined();
    expect(intelSection?.links.map((link) => link.label)).toEqual([
      "Projections hub",
      "KEI Lines board",
      "Edges desk",
      "Compare odds",
      "Props board",
      "Fantasy draft board",
      "MVP & OPOY race",
      "2026 NFL wall chart",
      "Team research hub",
      "League stats",
      "League standings",
      "Depth charts",
      "Injuries",
    ]);
    expect(intelSection?.links.every((link) => link.status === "active")).toBe(
      true,
    );
    expect(intelSection?.links.every((link) => link.premium)).toBe(true);
  });

  it("adds League Intel for non-NFL sports with sport-specific desks", () => {
    for (const sport of SPORTS.filter((s) => s.key !== "nfl")) {
      const content = buildSportOverviewContent(sport.key, sport.fullName);
      const sections = buildSportOverviewSections({
        sportKey: sport.key,
        base: `/pro/${sport.key}`,
        edgeBoardHref: `/edge-board/${sport.key}`,
        content,
      });
      expect(content.sectionTitles.market).toBe("Betting Desk");
      expect(sections.some((section) => section.title === "Team Intel")).toBe(
        false,
      );
      const intel = sections.find(
        (section) =>
          section.title === (content.sectionTitles.intel ?? "League Intel"),
      );
      expect(intel).toBeDefined();
      expect(
        intel?.links.some((link) => link.href === `/odds/${sport.key}`),
      ).toBe(true);
      expect(
        intel?.links.some((link) => link.href === `/edge-board/${sport.key}`),
      ).toBe(true);

      const desk = getSportDeskConfig(sport.key);
      expect(desk.cards).toHaveLength(3);
      expect(desk.pathLabel.length).toBeGreaterThan(0);
      expect(desk.footerCards.length).toBeGreaterThanOrEqual(2);
    }
  });

  it("keeps MLB props stake-gated as placeholder while exposing props center", () => {
    const content = buildSportOverviewContent("mlb", "MLB");
    const sections = buildSportOverviewSections({
      sportKey: "mlb",
      base: "/pro/mlb",
      edgeBoardHref: "/edge-board/mlb",
      content,
    });
    const propsSection = sections.find(
      (section) => section.title === content.sectionTitles.props,
    );
    expect(
      propsSection?.links.some((link) => link.status === "placeholder"),
    ).toBe(true);
    expect(
      propsSection?.links.some((link) => link.href === "/pro/props-center"),
    ).toBe(true);
  });

  it("builds placeholder props links for college sports", () => {
    const content = buildSportOverviewContent("cfb", "College Football");
    const sections = buildSportOverviewSections({
      sportKey: "cfb",
      base: "/pro/cfb",
      edgeBoardHref: "/edge-board/cfb",
      content,
    });
    const propsSection = sections.find(
      (section) => section.title === content.sectionTitles.props,
    );
    expect(propsSection?.links.length).toBeGreaterThan(0);
    expect(propsSection?.links.every((link) => !link.href)).toBe(true);
    expect(
      propsSection?.links.every((link) => link.status === "placeholder"),
    ).toBe(true);
  });

  it("requires line and total labels for article-ready cards", () => {
    expect(hasArticleData(buildRow())).toBe(true);
    expect(
      hasArticleData(
        buildRow({
          bestOU: {
            top: { label: "—", juice: "" },
            bottom: { label: "—", juice: "" },
          },
        }),
      ),
    ).toBe(false);
  });
});
