/**
 * Product 2026-10-27 — O4 Coming Soon / NO-GO.
 * Season-engine / fantasy subscriber surfaces must not paint win%,
 * expected_total_mean, projections, or TruePR while public numbers
 * are disabled. Do not flip NFL_EDGE_BOARD_PUBLIC_ENABLED.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
  customerCtaHref,
  isFootballPublicNumberHref,
  isFootballPublicNumbersDisabled,
} from "@/lib/cfb-edge-board-public";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

const O4_PAGES = [
  {
    rel: "app/(pro)/pro/nfl/game-boxes/page.tsx",
    title: "NFL Game Boxes",
    fetch: "loadSeasonEngineMatchups",
  },
  {
    rel: "app/(pro)/pro/nfl/dfs/page.tsx",
    title: "NFL DFS",
    fetch: "fetchNflDfsBoard",
  },
  {
    rel: "app/(pro)/pro/nfl/projections/page.tsx",
    title: "NFL Futures",
    fetch: "loadPlayerSeasonTotalsSpine",
  },
  {
    rel: "app/(pro)/pro/nfl/weekly-fantasy/page.tsx",
    title: "NFL Weekly Fantasy",
    fetch: "loadPlayerSeasonTotalsSpine",
  },
  {
    rel: "app/(pro)/pro/nfl/model/page.tsx",
    title: "NFL Season Model",
    fetch: "fetchTruePrProductSurface",
  },
] as const;

const O4_HREFS = [
  "/pro/nfl/game-boxes",
  "/pro/nfl/dfs",
  "/pro/nfl/projections",
  "/pro/nfl/weekly-fantasy",
  "/pro/nfl/model",
] as const;

describe("O4 NFL public-kill on season-engine/fantasy surfaces", () => {
  afterEach(() => {
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
  });

  it("keeps the public constant off and kill on by default", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(true);
  });

  it("each O4 page fail-closes with Coming Soon before number fetch/paint", () => {
    for (const page of O4_PAGES) {
      const src = readRel(page.rel);
      expect(src, page.rel).toContain("isFootballPublicNumbersDisabled");
      expect(src, page.rel).toContain("FootballNumbersUnavailable");
      expect(src, page.rel).toContain("Coming soon");
      expect(src, page.rel).toContain(`title="${page.title}"`);
      expect(
        src.indexOf("isFootballPublicNumbersDisabled"),
        page.rel,
      ).toBeLessThan(src.indexOf(page.fetch));
      expect(src, page.rel).not.toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED");
    }
  });

  it("DFS and game-boxes fetch helpers gate before model-service reads", () => {
    const dfs = readRel("lib/nfl-dfs-board.ts");
    expect(dfs).toContain("isFootballPublicNumbersDisabled");
    expect(dfs.indexOf("isFootballPublicNumbersDisabled")).toBeLessThan(
      dfs.indexOf("MODEL_SERVICE_URL"),
    );
    expect(dfs.indexOf("isFootballPublicNumbersDisabled")).toBeLessThan(
      dfs.indexOf("/nfl/dfs/board"),
    );

    const engine = readRel("lib/nfl-season-engine.ts");
    expect(engine).toContain("isFootballPublicNumbersDisabled");
    const gameBoxesFn = engine.indexOf(
      "export async function fetchSeasonEngineGameBoxes",
    );
    const matchupsFn = engine.indexOf(
      "export async function loadSeasonEngineMatchups",
    );
    expect(gameBoxesFn).toBeGreaterThan(-1);
    expect(matchupsFn).toBeGreaterThan(-1);
    expect(
      engine.indexOf("isFootballPublicNumbersDisabled", gameBoxesFn),
    ).toBeLessThan(engine.indexOf("/nfl/season-engine/game-boxes"));
    expect(
      engine.indexOf("isFootballPublicNumbersDisabled", matchupsFn),
    ).toBeLessThan(engine.indexOf("fetchNflFairLines", matchupsFn));

    const api = readRel("app/api/nfl/season-engine/game-boxes/route.ts");
    expect(api).toContain("isFootballPublicNumbersDisabled");
    expect(api).toContain("status: 503");
  });

  it("game-boxes client does not paint Home win or expected_total when kill is on", () => {
    const client = readRel(
      "components/pro/nfl/SeasonEngineGameBoxesClient.tsx",
    );
    expect(client).toContain("isFootballPublicNumbersDisabled");
    expect(client).toContain("publicNumbersDisabled");
    expect(client).toContain("home_win_prob_mean");
    expect(client).toContain("expected_total_mean");
    expect(client).toMatch(/game_script_summary && !publicNumbersDisabled/);
    expect(client.indexOf("isFootballPublicNumbersDisabled")).toBeLessThan(
      client.indexOf("home_win_prob_mean"),
    );
    expect(client.indexOf("if (publicNumbersDisabled)")).toBeLessThan(
      client.indexOf("home_win_prob_mean"),
    );

    const truePr = readRel("components/pro/nfl/TruePrDriversBoard.tsx");
    expect(truePr).toContain("isFootballPublicNumbersDisabled");
    expect(truePr.indexOf("isFootballPublicNumbersDisabled")).toBeLessThan(
      truePr.indexOf("surface.teams.map"),
    );
  });

  it("strips O4 customer hrefs while Coming Soon is on", () => {
    for (const href of O4_HREFS) {
      expect(isFootballPublicNumberHref(href), href).toBe(true);
      expect(customerCtaHref(href), href).toBeNull();
    }
    expect(isFootballPublicNumberHref("/pro/nfl/survivor")).toBe(false);
    expect(customerCtaHref("/pro/nfl/survivor")).toBe("/pro/nfl/survivor");
    expect(customerCtaHref("/pro/cfb/line-curve")).toBe("/pro/cfb/line-curve");

    const deskNav = readRel("components/pro/nfl/fantasy/FantasyDeskNav.tsx");
    expect(deskNav).toContain("withoutFootballPublicNumberHrefs");
  });

  it("internal override restores O4 hrefs without flipping the public constant", () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    process.env.NFL_EDGE_BOARD_INTERNAL = "1";
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(false);
    for (const href of O4_HREFS) {
      expect(customerCtaHref(href), href).toBe(href);
    }
  });

  it("does not expand frozen #632/#633 or flip the public flag", () => {
    const pub = readRel("lib/cfb-edge-board-public.ts");
    expect(pub).toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).toContain("CoS CLEAR");

    const props = readRel("app/(pro)/pro/nfl/props/page.tsx");
    expect(props).not.toContain("isFootballPublicNumbersDisabled");
    expect(props).not.toContain("FootballNumbersUnavailable");

    const edges = readRel("app/(pro)/pro/nfl/edges/page.tsx");
    expect(edges).toContain("isFootballPublicNumbersDisabled");
  });
});
