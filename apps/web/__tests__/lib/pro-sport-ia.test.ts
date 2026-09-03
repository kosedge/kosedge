import { readFileSync } from "node:fs";
import path from "node:path";
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

const NFL_SECTION_STRUCTURE: Record<string, string[]> = {
  "Weekly Slate": ["Weekly Slate", "Camp Desk", "Team Previews"],
  "Betting Desk": [
    "KEI Lines",
    "Edges",
    "Props",
    "Compare Odds",
    "Futures",
    "MVP/Awards",
  ],
  Fantasy: [
    "Fantasy Draft Desk",
    "Weekly Fantasy",
    "DFS Board",
    "Guillotine League",
    "Sleepers",
    "Pick’em",
  ],
  "Team Intel": [
    "Team Research Hub",
    "Power Ratings",
    "Standings",
    "League Stats",
    "Depth Charts",
    "Injuries & News",
  ],
  "Model Governance & Health": [
    "Model Transparency",
    "Sport Tracking",
    "Global CLV Tracker",
    "Performance",
  ],
};

describe("pro sport IA", () => {
  it("marks college sports as props-disabled", () => {
    expect(supportsPropsFantasy("ncaam")).toBe(false);
    expect(supportsPropsFantasy("cfb")).toBe(false);
    expect(supportsPropsFantasy("nfl")).toBe(true);
  });

  it("builds the exact NFL hub nav structure without duplicate categories", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });

    expect(sections.map((section) => section.title)).toEqual(
      Object.keys(NFL_SECTION_STRUCTURE),
    );

    for (const [title, labels] of Object.entries(NFL_SECTION_STRUCTURE)) {
      const section = sections.find((item) => item.title === title);
      expect(section?.links.map((link) => link.label)).toEqual(labels);
    }

    const allLabels = sections.flatMap((section) =>
      section.links.map((link) => `${section.title}::${link.label}`),
    );
    expect(new Set(allLabels).size).toBe(allLabels.length);

    expect(content.sectionTitles.props).toBe("Fantasy");
    expect(content.sectionTitles.intel).toBe("Team Intel");
  });

  it("wires NFL hub links to real routes", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    const byLabel = Object.fromEntries(
      sections.flatMap((section) =>
        section.links.map((link) => [link.label, link.href]),
      ),
    );

    expect(byLabel["Weekly Slate"]).toBe("/pro/nfl/slate/today");
    expect(byLabel["Camp Desk"]).toBe("/pro/nfl/camp");
    expect(byLabel["Team Previews"]).toBe("/pro/nfl/previews");
    expect(byLabel["Player Previews"]).toBeUndefined();
    expect(byLabel["KEI Lines"]).toBe("/pro/nfl/fair-lines");
    expect(byLabel["Compare Odds"]).toBe("/odds/nfl");
    expect(byLabel.Edges).toBe("/pro/nfl/edges");
    expect(byLabel.Props).toBe("/pro/nfl/props");
    expect(byLabel["MVP/Awards"]).toBe("/pro/nfl/awards");
    expect(byLabel["Prediction Markets"]).toBeUndefined();
    expect(byLabel["Execution Monitor"]).toBeUndefined();
    expect(byLabel.Futures).toBe("/pro/nfl/projections");
    expect(byLabel["Player Props Board"]).toBeUndefined();
    expect(byLabel["Fantasy Draft Desk"]).toBe("/pro/nfl/fantasy");
    expect(byLabel["Weekly Fantasy"]).toBe("/pro/nfl/weekly-fantasy");
    expect(byLabel["DFS Board"]).toBe("/pro/nfl/dfs");
    expect(byLabel["Guillotine League"]).toBe("/pro/nfl/fantasy/guillotine");
    expect(byLabel.Sleepers).toBe("/pro/nfl/fantasy/sleepers");
    expect(byLabel["Pick’em"]).toBe("/pro/nfl/fantasy/pickem");

    const fantasy = sections.find((section) => section.title === "Fantasy");
    expect(fantasy?.subtitle).toMatch(/weekly ATS pick/i);
    expect(fantasy?.subtitle).not.toMatch(/\bSU\b/);
    const pickem = fantasy?.links.find((link) => link.label === "Pick’em");
    expect(pickem?.hint).toMatch(/Weekly ATS card/i);
    expect(pickem?.hint).not.toMatch(/\bSU\b/);
    // Unfinished tools stay visible — copy-match only; do not hide tiles.
    expect(fantasy?.links.map((link) => link.label)).toEqual(
      NFL_SECTION_STRUCTURE.Fantasy,
    );
    expect(fantasy?.links.every((link) => link.status === "active")).toBe(true);
    expect(byLabel["Team Research Hub"]).toBe("/pro/nfl/teams");
    expect(byLabel["Power Ratings"]).toBe("/pro/power-ratings/nfl");
    expect(byLabel.Standings).toBe("/pro/nfl/standings");
    expect(byLabel["League Stats"]).toBe("/pro/nfl/stats");
    expect(byLabel["Depth Charts"]).toBe("/pro/nfl/depth-charts");
    expect(byLabel["Injuries & News"]).toBe("/pro/nfl/injuries");
    expect(byLabel["Model Transparency"]).toBe("/pro/model-transparency");
    expect(byLabel["Sport Tracking"]).toBe("/pro/nfl/tracking");
    const tracking = sections
      .flatMap((section) => section.links)
      .find((link) => link.label === "Sport Tracking");
    expect(tracking?.hint).toMatch(/incomplete/i);
    expect(byLabel["Global CLV Tracker"]).toBe("/pro/clv-tracker");
    expect(byLabel.Performance).toBe("/pro/model-transparency");

    expect(
      sections
        .flatMap((section) => section.links)
        .every((link) => link.href && link.status === "active"),
    ).toBe(true);
  });

  it("keeps unfinished NFL Overview catalog tiles active with honest marketing copy", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    const byLabel = Object.fromEntries(
      sections.flatMap((section) =>
        section.links.map((link) => [link.label, link]),
      ),
    );

    const requiredActive = [
      "Weekly Fantasy",
      "DFS Board",
      "Guillotine League",
      "MVP/Awards",
      "Depth Charts",
      "Performance",
    ] as const;
    for (const label of requiredActive) {
      expect(byLabel[label]?.status).toBe("active");
      expect(byLabel[label]?.href).toBeTruthy();
    }

    const weeklyFantasy = byLabel["Weekly Fantasy"]!;
    expect(weeklyFantasy.hint).toMatch(/season-rate/i);
    expect(weeklyFantasy.hint).toMatch(/not week-specific/i);
    expect(weeklyFantasy.label).not.toMatch(/projections/i);
    expect(weeklyFantasy.hint.toLowerCase()).not.toContain(
      "weekly leaders and player fantasy totals",
    );

    const dfs = byLabel["DFS Board"]!;
    expect(dfs.hint).toMatch(/no live slate/i);
    expect(dfs.hint).toMatch(/salaries/i);
    expect(dfs.hint).toMatch(/ownership/i);
    expect(dfs.hint.toLowerCase()).not.toMatch(
      /salary, projection, value, and ownership/,
    );

    const awards = byLabel["MVP/Awards"]!;
    expect(awards.hint).not.toMatch(/live award races/i);
    expect(awards.hint).toMatch(/snapshot|odds not joined/i);

    const guillotine = byLabel["Guillotine League"]!;
    expect(guillotine.hint).toMatch(/educational stay-alive/i);
    expect(guillotine.hint).toMatch(/not a weekly elimination/i);

    const performance = byLabel.Performance!;
    expect(performance.hint).toMatch(/Performance page TBD/i);
    expect(performance.href).toBe("/pro/model-transparency");

    const fantasy = sections.find((section) => section.title === "Fantasy");
    expect(fantasy?.subtitle).toMatch(/educational guillotine/i);
  });

  it("labels NFL Overview matchup briefs as pending (not a finished brief desk)", () => {
    const src = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/nfl/overview/page.tsx"),
      "utf8",
    );
    expect(src).toMatch(/matchup briefs pending/i);
    expect(src).not.toMatch(
      /Matchup briefs, slate snapshot, and game cards — the weekly desk/,
    );
  });

  it("keeps Guillotine destination honest: educational lists, not weekly elimination/waiver", () => {
    const src = readFileSync(
      path.join(
        __dirname,
        "../../app/(pro)/pro/nfl/fantasy/guillotine/page.tsx",
      ),
      "utf8",
    );
    expect(src).toMatch(/Educational stay-alive lists from season ranks/i);
    expect(src).toMatch(/not a weekly\s+elimination or waiver tool/i);
    expect(src).not.toMatch(
      /Last place is eliminated each week — waivers and adds matter as much as your draft/,
    );
    expect(src).not.toMatch(/Each week, the lowest-scoring team is cut/);
    expect(src).not.toMatch(/Waivers and opportunistic adds matter weekly/);
    // Same stale editorial launch date killed on props (PR 419).
    expect(src).not.toMatch(/\bKOSEDGE_DATE\b/);
    expect(src).not.toContain("August 11, 2026");
    expect(src).not.toMatch(/Date:\s*\{/);
  });

  it("keeps Weekly Fantasy destination H1 honest: season-rate PPG, not week projections", () => {
    const src = readFileSync(
      path.join(__dirname, "../../app/(pro)/pro/nfl/weekly-fantasy/page.tsx"),
      "utf8",
    );
    expect(src).toMatch(/Season-rate PPG/i);
    expect(src).toMatch(/not week-specific projections/i);
    expect(src).toMatch(/Season-rate PPG leaders/);
    expect(src).not.toMatch(/Weekly Fantasy Projections/);
    expect(src).not.toMatch(/>Weekly leaders</);
    // Weekly Fantasy never had editorial Aug 11 chrome — keep it gone.
    expect(src).not.toMatch(/\bKOSEDGE_DATE\b/);
    expect(src).not.toContain("August 11, 2026");
  });

  it("keeps Team Intel free of betting-desk / props duplicates", () => {
    const content = buildSportOverviewContent("nfl", "NFL");
    const sections = buildSportOverviewSections({
      sportKey: "nfl",
      base: "/pro/nfl",
      edgeBoardHref: "/edge-board/nfl",
      content,
    });
    const intel = sections.find((section) => section.title === "Team Intel");
    const labels = intel?.links.map((link) => link.label) ?? [];
    expect(labels).not.toContain("KEI Lines");
    expect(labels).not.toContain("Edges");
    expect(labels).not.toContain("Props board");
    expect(labels).not.toContain("Compare odds");
    expect(labels).not.toContain("Fantasy draft board");
    expect(labels).not.toContain("Projections hub");
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
    expect(
      marketSection?.links.find((link) => link.label === "KEI Lines")?.href,
    ).toBe("/pro/nfl/fair-lines");
    expect(
      marketSection?.links.find((link) => link.label === "Edges")?.href,
    ).toBe("/pro/nfl/edges");
    expect(
      marketSection?.links.find((link) => link.label === "Props")?.href,
    ).toBe("/pro/nfl/props");
    expect(marketSection?.links.map((link) => link.label)).toEqual([
      "KEI Lines",
      "Edges",
      "Props",
      "Compare Odds",
      "Futures",
      "MVP/Awards",
    ]);
  });

  it("locks NFL research tools footer to the 3×2 IA grid", () => {
    const desk = getSportDeskConfig("nfl");
    expect(desk.footerCards.map((c) => c.title)).toEqual([
      "Team Previews",
      "Season Model",
      "Game Boxes",
      "Model Transparency",
      "Wall Chart",
      "KEI Lines",
    ]);
    expect(desk.footerCards.some((c) => c.title === "Power Ratings")).toBe(
      false,
    );
    const gameBoxes = desk.footerCards.find((c) => c.title === "Game Boxes");
    expect(gameBoxes?.description.toLowerCase()).not.toMatch(/p10/);
    expect(gameBoxes?.description.toLowerCase()).toContain("typical range");
  });

  it("CFB hub footer advertises published KEI with research-fair model", () => {
    const desk = getSportDeskConfig("cfb");
    const edge = desk.footerCards.find((c) => c.title === "Public Edge Board");
    expect(edge?.description.toLowerCase()).toContain("kei vs trusted market");
    expect(edge?.description.toLowerCase()).toContain("research-fair");
    expect(edge?.description.toLowerCase()).not.toContain(
      "directional edge tags",
    );
    const kei = desk.footerCards.find((c) => c.title === "KEI Lines");
    expect(kei?.description.toLowerCase()).toContain("published cfb kei");
    expect(kei?.description.toLowerCase()).not.toContain(
      "projected spread/total baselines",
    );
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

  it("omits props walls for college sports (no forced props on NCAAM/CFB)", () => {
    for (const sportKey of ["cfb", "ncaam"] as const) {
      const content = buildSportOverviewContent(
        sportKey,
        sportKey.toUpperCase(),
      );
      const sections = buildSportOverviewSections({
        sportKey,
        base: `/pro/${sportKey}`,
        edgeBoardHref: `/edge-board/${sportKey}`,
        content,
      });
      const propsSection = sections.find(
        (section) =>
          section.title === content.sectionTitles.props ||
          section.title.toLowerCase().includes("props"),
      );
      expect(propsSection).toBeUndefined();
    }
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
