import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  fetchNflFairLines,
  inspectOwnedNflFairLinesOddsEvents,
  inspectOwnedNflFairLinesOddsPayload,
  NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED,
  NFL_FAIR_LINES_REUSE_EVENTS_UNAVAILABLE,
  NFL_FAIR_LINES_REUSE_PAYLOAD_UNAVAILABLE,
  NFL_FAIR_LINES_REUSE_UNAVAILABLE,
  NflFairLinesUnavailableError,
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

  it("assemble fair-lines caller is skip+persist0 (overlay cannot join)", () => {
    const src = readApp("lib/build-edge-board-rows.ts");
    expect(src).toContain('oddsMode: "skip"');
    expect(src).toContain("persistOdds: false");
    expect(src).not.toContain('oddsMode: "live"');
    expect(src).not.toContain("persistOdds: true");
    expect(src).not.toContain("oddsPayload:");
    expect(src).not.toContain("ownedNflFairLinesFixtureRows");
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

  it("refuses overlay odds_payload reuse before upstream", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsPayload: [{ game: "NE @ SEA", market: "Spread" }],
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_REUSE_PAYLOAD_UNAVAILABLE);
  });

  it("does not discard a nonempty overlay payload when events are otherwise present", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsEvents: [
        {
          id: "evt-1",
          sport_key: "americanfootball_nfl",
          commence_time: "2026-09-13T17:00:00Z",
          home_team: "Seattle Seahawks",
          away_team: "New England Patriots",
          bookmakers: [
            {
              key: "draftkings",
              last_update: "2026-09-10T14:00:00Z",
              markets: [
                {
                  key: "spreads",
                  last_update: "2026-09-10T14:00:00Z",
                  outcomes: [
                    { name: "Seattle Seahawks", point: -3.5, price: -110 },
                    { name: "New England Patriots", point: 3.5, price: -110 },
                  ],
                },
              ],
            },
          ],
        },
      ],
      oddsPayload: [{ game: "NE @ SEA", market: "Spread" }],
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_REUSE_PAYLOAD_UNAVAILABLE);
  });

  it("does not discard a malformed events channel when payload is absent", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const board = await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsEvents: [{ home_team: {}, market: 1, bookmakers: [] }],
    });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(board.error).toBe(NFL_FAIR_LINES_REUSE_EVENTS_UNAVAILABLE);
  });

  it("POSTs reuse persist=0 with exact odds_events when that channel alone is valid", async () => {
    const events = [
      {
        id: "evt-1",
        sport_key: "americanfootball_nfl",
        commence_time: "2026-09-13T17:00:00Z",
        home_team: "Seattle Seahawks",
        away_team: "New England Patriots",
        bookmakers: [
          {
            key: "draftkings",
            last_update: "2026-09-10T14:00:00Z",
            markets: [
              {
                key: "spreads",
                last_update: "2026-09-10T14:00:00Z",
                outcomes: [
                  { name: "Seattle Seahawks", point: -3.5, price: -110 },
                  { name: "New England Patriots", point: 3.5, price: -110 },
                ],
              },
            ],
          },
        ],
      },
    ];
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const href = String(input);
        expect(href).toContain("persist=0");
        expect(href).toContain("odds_mode=reuse");
        expect(String(init?.method || "GET").toUpperCase()).toBe("POST");
        const body = JSON.parse(String(init?.body || "{}"));
        expect(body.odds_mode).toBe("reuse");
        expect(body.persist).toBe(0);
        expect(body.odds_events).toEqual(events);
        expect(body.odds_payload).toEqual([]);
        return new Response(
          JSON.stringify({
            season: 2026,
            count: 0,
            lines: [],
            odds_as_of: "2026-09-10T14:00:00Z",
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
      oddsEvents: events,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(board.error).toBeUndefined();
    expect(board.oddsAsOf).toBe("2026-09-10T14:00:00Z");
  });

  it("inspectors: absence is distinct from malformed (B owns fuller cases)", () => {
    expect(inspectOwnedNflFairLinesOddsEvents(undefined).status).toBe("absent");
    expect(inspectOwnedNflFairLinesOddsEvents([]).status).toBe("absent");
    expect(inspectOwnedNflFairLinesOddsEvents([{ home_team: {} }]).status).toBe(
      "malformed",
    );
    expect(inspectOwnedNflFairLinesOddsPayload(undefined).status).toBe("absent");
    expect(inspectOwnedNflFairLinesOddsPayload([]).status).toBe("absent");
    expect(
      inspectOwnedNflFairLinesOddsPayload([{ game: "NE @ SEA", market: "Spread" }])
        .status,
    ).toBe("malformed");
    expect(NFL_FAIR_LINES_REUSE_UNAVAILABLE).toMatch(/unavailable/i);
  });
});
