import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  fetchNflFairLines,
  NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED,
  NFL_FAIR_LINES_REUSE_UNAVAILABLE,
  NflFairLinesUnavailableError,
  ownedNflFairLinesFixtureRows,
} from "@/lib/nfl-fair-lines";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";

const root = process.cwd();

function readApp(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

const SUBSCRIBER_CALLERS = [
  "app/api/nfl/fair-lines/route.ts",
  "lib/nfl-edges.ts",
  "lib/nfl-slate.ts",
  "lib/nfl-season-engine.ts",
  "lib/resolve-kei-lines.ts",
  "app/api/nfl/season-engine/survivor/plan/route.ts",
  "app/api/nfl/season-engine/survivor/route.ts",
  "app/(pro)/pro/nfl/fantasy/pickem/page.tsx",
  "app/(pro)/pro/prediction-market/page.tsx",
  "app/(pro)/pro/[sport]/execution/page.tsx",
] as const;

describe("WEB_OWNED_ONLY_R1 fetchNflFairLines", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("helper source never defaults to live and never grants persist=1", () => {
    const src = readApp("lib/nfl-fair-lines.ts");
    expect(src).not.toMatch(/oddsMode\s*=\s*params\.oddsMode\s*\?\?\s*"live"/);
    expect(src).toContain('params.oddsMode ?? "skip"');
    expect(src).not.toMatch(/persistOdds\s*\?\s*"1"/);
    expect(src).toContain('url.searchParams.set("persist", "0")');
    expect(src).toContain('url.searchParams.set("odds_mode", useReusePost ? "reuse" : "skip")');
    expect(src).not.toMatch(/process\.env\.[A-Z0-9_]*ODDS/);
    expect(src).not.toMatch(/NFL_FAIR_LINES_LIVE/);
    expect(src).not.toMatch(/ALLOW_.*PERSIST/);
  });

  it("every subscriber caller sets oddsMode skip and persistOdds false", () => {
    for (const rel of SUBSCRIBER_CALLERS) {
      const src = readApp(rel);
      expect(src, rel).toContain('oddsMode: "skip"');
      expect(src, rel).toContain("persistOdds: false");
      expect(src, rel).not.toContain('oddsMode: "live"');
      expect(src, rel).not.toContain("persistOdds: true");
    }
  });

  it("assemble reuse is owned-fixture gated (no live fallthrough)", () => {
    const src = readApp("lib/build-edge-board-rows.ts");
    expect(src).toContain("ownedNflFairLinesFixtureRows");
    expect(src).toContain('oddsMode: "reuse"');
    expect(src).toContain('oddsMode: "skip"');
    expect(src).toContain("persistOdds: false");
    expect(src).not.toContain('oddsMode: "live"');
    expect(src).not.toContain("persistOdds: true");
  });

  it("refuses oddsMode=live before upstreamFetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "live",
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED);
    expect(board.count).toBe(0);
    expect(board.lines).toEqual([]);
    expect(board.oddsAsOf).toBeNull();
  });

  it("throws typed unavailable for live + throwOnTransportError (page-data 503)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(
      fetchNflFairLines({
        season: 2026,
        oddsMode: "live",
        throwOnTransportError: true,
      }),
    ).rejects.toBeInstanceOf(NflFairLinesUnavailableError);
    expect(fetchMock).not.toHaveBeenCalled();

    const res = pageDataUpstreamErrorResponse(
      new NflFairLinesUnavailableError(NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED),
    );
    expect(res.status).toBe(503);
    const body = (await res.json()) as { error?: string };
    expect(body.error).toBe(NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED);
    expect(body).not.toHaveProperty("count");
  });

  it("refuses empty reuse before upstream (no GET odds_mode=reuse live fallthrough)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_REUSE_UNAVAILABLE);
    expect(board.count).toBe(0);
  });

  it("refuses malformed reuse payload before upstream", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsPayload: [null, "x", 1],
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_REUSE_UNAVAILABLE);
  });

  it("refuses unidentified object rows as malformed reuse", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsPayload: [{ foo: "bar" }],
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_REUSE_UNAVAILABLE);
  });

  it("POSTs reuse persist=0 only with validated owned fixture", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const href = String(input);
        expect(href).toContain("persist=0");
        expect(href).toContain("odds_mode=reuse");
        expect(href).not.toMatch(/persist=1/);
        expect(String(init?.method || "GET").toUpperCase()).toBe("POST");
        const body = JSON.parse(String(init?.body || "{}"));
        expect(body.odds_mode).toBe("reuse");
        expect(body.persist).toBe(0);
        expect(body.odds_payload).toEqual([
          { game: "NE @ SEA", market: "Spread" },
        ]);
        return new Response(
          JSON.stringify({
            season: 2026,
            count: 0,
            lines: [],
            odds_as_of: "2026-09-03T14:00:00Z",
            diagnostics: { odds_mode: "reuse" },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsPayload: [{ game: "NE @ SEA", market: "Spread" }],
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(board.error).toBeUndefined();
    expect(board.oddsAsOf).toBe("2026-09-03T14:00:00Z");
  });

  it("owned fixture validator accepts identity rows and rejects empty/malformed", () => {
    expect(
      ownedNflFairLinesFixtureRows([{ game: "NE @ SEA", market: "Spread" }]),
    ).toHaveLength(1);
    expect(
      ownedNflFairLinesFixtureRows([
        { home_team: "Seattle Seahawks", away_team: "New England Patriots" },
      ]),
    ).toHaveLength(1);
    expect(ownedNflFairLinesFixtureRows([])).toBeNull();
    expect(ownedNflFairLinesFixtureRows(undefined)).toBeNull();
    expect(ownedNflFairLinesFixtureRows([{}])).toBeNull();
    expect(ownedNflFairLinesFixtureRows(["x"])).toBeNull();
  });
});
