/**
 * Product 2026-10-26 — NFL Coming Soon / NO-GO.
 * Weekly props must stay dark when LIVE is false and/or public numbers
 * are disabled. Either control alone cannot reopen subscriber fair/edge.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { isFootballPublicNumbersDisabled } from "@/lib/cfb-edge-board-public";
import {
  edgesMayShowPropRows,
  nflPropsSurfaceState,
  nflWeeklyPropsBoardMayFetch,
} from "@/lib/nfl-props-surface";
import {
  NFL_WEEKLY_PROPS_LIVE,
  NFL_WEEKLY_PROPS_PATH_COHERENT,
} from "@/lib/nfl-weekly-props-live";

const webRoot = path.join(__dirname, "../..");

function readRel(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("NFL weekly props Coming Soon fail-closed", () => {
  afterEach(() => {
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
  });

  it("LIVE is false and public numbers are disabled by default", () => {
    expect(NFL_WEEKLY_PROPS_LIVE).toBe(false);
    expect(NFL_WEEKLY_PROPS_PATH_COHERENT).toBe("gated");
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(true);
    expect(nflWeeklyPropsBoardMayFetch()).toBe(false);
  });

  it("either control alone keeps the board from fetching", () => {
    expect(
      nflWeeklyPropsBoardMayFetch({
        live: true,
        publicNumbersDisabled: true,
      }),
    ).toBe(false);
    expect(
      nflWeeklyPropsBoardMayFetch({
        live: false,
        publicNumbersDisabled: false,
      }),
    ).toBe(false);
    expect(
      nflWeeklyPropsBoardMayFetch({
        live: false,
        publicNumbersDisabled: true,
      }),
    ).toBe(false);
    expect(
      nflWeeklyPropsBoardMayFetch({
        live: true,
        publicNumbersDisabled: false,
      }),
    ).toBe(true);
  });

  it("internal public-numbers override cannot reopen while LIVE is false", () => {
    process.env.NFL_EDGE_BOARD_INTERNAL = "1";
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(false);
    expect(NFL_WEEKLY_PROPS_LIVE).toBe(false);
    expect(nflWeeklyPropsBoardMayFetch()).toBe(false);
  });

  it("Edges will not paint prop fair/edge while the board is dark", () => {
    expect(
      edgesMayShowPropRows(
        nflPropsSurfaceState({
          rows: [{ marketJoined: true }],
          diagnostics: { notLive: false, marketJoinedCount: 1 },
        }),
      ),
    ).toBe(false);
  });

  it("page fail-closes with Coming Soon before fetchNflPropsBoard", () => {
    const page = readRel("app/(pro)/pro/nfl/props/page.tsx");
    expect(page).toContain("isFootballPublicNumbersDisabled");
    expect(page).toContain("FootballNumbersUnavailable");
    expect(page).toContain("Coming soon");
    expect(page).toContain('title="NFL Props"');
    expect(page.indexOf("isFootballPublicNumbersDisabled")).toBeLessThan(
      page.indexOf("fetchNflPropsBoard"),
    );
  });

  it("fetch path gates on LIVE and isFootballPublicNumbersDisabled before MODEL_SERVICE_URL", () => {
    const fetchSrc = readRel("lib/nfl-props-board.ts");
    expect(fetchSrc).toContain("NFL_WEEKLY_PROPS_LIVE");
    expect(fetchSrc).toContain("isFootballPublicNumbersDisabled");
    expect(fetchSrc.indexOf("isFootballPublicNumbersDisabled")).toBeLessThan(
      fetchSrc.indexOf("MODEL_SERVICE_URL"),
    );
    expect(fetchSrc.indexOf("boardDark")).toBeLessThan(
      fetchSrc.indexOf("MODEL_SERVICE_URL"),
    );
    expect(fetchSrc.indexOf("boardDark")).toBeLessThan(
      fetchSrc.indexOf("/nfl/props/board"),
    );
    expect(fetchSrc).not.toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED");
  });

  it("line-curve GET already fail-closes without a model bind", () => {
    const get = readRel("app/api/line-curve/route.ts");
    expect(get).toContain("GET cannot carry a model bind or snapshot");
    expect(get).toContain("missing_model_run");
    expect(get).toContain("Never live-fetch Odds API");
    expect(get).not.toContain("fetchNflPropsBoard");
    expect(get).not.toContain("allowLiveOddsFetch");
  });

  it("does not expand into DFS, game-boxes, T7, injury, or holdout", () => {
    const page = readRel("app/(pro)/pro/nfl/props/page.tsx");
    const fetchSrc = readRel("lib/nfl-props-board.ts");
    const surface = readRel("lib/nfl-props-surface.ts");
    const blob = `${page}\n${fetchSrc}\n${surface}`;
    expect(blob).not.toMatch(/T7|injury overlay|holdout/i);
    expect(page).not.toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED");
  });
});
