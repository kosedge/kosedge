import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  DUMMY_ODDS_KEY,
  installOddsHostFailOnHit,
  stubDummyOddsKeys,
} from "@/__tests__/helpers/authorized-odds-job";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(async () => "authorized"),
}));

stubDummyOddsKeys();

const root = path.resolve(process.cwd());

function src(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

describe("G-PROXY-LIVE / G-CFB-RAIL-LIVE / G-S6 / G-S7 / G-NCAAM source locks", () => {
  it("web fair-lines default is skip and live is coerced", () => {
    const fair = src("lib/nfl-fair-lines.ts");
    expect(fair).toContain('params.oddsMode ?? "skip"');
    expect(fair).not.toContain('params.oddsMode ?? "live"');
    expect(fair).toContain('requestedMode === "live" ? "skip"');
    expect(fair).toContain('url.searchParams.set("odds_mode", oddsMode)');
  });

  it("user-read fair-lines callers do not pass oddsMode live", () => {
    const files = [
      "app/(pro)/pro/prediction-market/page.tsx",
      "app/(pro)/pro/[sport]/execution/page.tsx",
      "app/api/nfl/season-engine/survivor/route.ts",
      "lib/nfl-season-engine.ts",
      "lib/resolve-kei-lines.ts",
      "lib/nfl-edges.ts",
      "app/api/nfl/fair-lines/route.ts",
    ];
    for (const rel of files) {
      const text = src(rel);
      expect(text).toContain("fetchNflFairLines");
      expect(text).not.toMatch(/oddsMode:\s*"live"/);
    }
  });

  it("CFB request route hard-denies live pull", () => {
    const cfb = readFileSync(
      path.join(root, "../../services/model-service/src/routes/cfb.py"),
      "utf8",
    );
    expect(cfb).toContain("allow_live=False");
    expect(cfb).not.toMatch(/return current_cfb_odds_events\(\s*\)/);
  });

  it("nfl/mlb edges/today request path is C8-gated (user-read Railway hop)", () => {
    const nfl = readFileSync(
      path.join(root, "../../services/model-service/src/routes/nfl.py"),
      "utf8",
    );
    const mlb = readFileSync(
      path.join(root, "../../services/model-service/src/routes/mlb.py"),
      "utf8",
    );
    expect(nfl).toContain("request_path_paid_odds_allowed");
    expect(mlb).toContain("request_path_paid_odds_allowed");
    const nflEdges = nfl.slice(
      nfl.indexOf("def nfl_edges_today"),
      nfl.indexOf("def _normalize_nfl_fair_lines_odds_mode"),
    );
    expect(nflEdges).toContain("if not request_path_paid_odds_allowed()");
    expect(nflEdges).toContain('odds_feed_error = "paid_fetch_denied"');
    const mlbEdges = mlb.slice(
      mlb.indexOf("def mlb_edges_today"),
      mlb.indexOf("def mlb_premium_feed"),
    );
    expect(mlbEdges).toContain("if not request_path_paid_odds_allowed()");
    expect(mlbEdges).toContain('reason": "paid_fetch_denied"');
  });

  it("client boards do not import odds-api / odds-acquire (async_hooks)", () => {
    const clients = [
      "components/pro/nfl/NflEdgesDeskClient.tsx",
      "components/pro/nfl/NflFairLinesClient.tsx",
      "components/OddsCompareBoard.tsx",
    ];
    for (const rel of clients) {
      const text = src(rel);
      expect(text).toMatch(/["']use client["']/);
      expect(text).not.toMatch(
        /import\s+(?!type\s)[^;]*from\s+["']@\/lib\/odds-api["']/,
      );
      expect(text).not.toContain("@/lib/odds-acquire");
    }
    expect(src("lib/odds-acquire/acquire.ts")).toContain(
      'import "server-only"',
    );
  });

  it("ncaam user-read route does not proxy Railway live Odds", () => {
    const ncaam = src("app/api/edge-board/ncaam/today/route.ts");
    expect(ncaam).not.toMatch(/fetch\([^)]*ncaam\/today/);
    expect(ncaam).not.toContain("tryModelService");
    expect(ncaam).toContain("paid_fetch_denied");
  });

  it("line-curve POST does not price a client snapshot", () => {
    const route = src("app/api/line-curve/route.ts");
    expect(route).not.toContain("getLineCurve");
    expect(route).not.toContain("classifyAltSnapshot");
    expect(route).toContain("G-S6-CLIENT-SNAP");
    expect(route).toContain("lineCurveUnavailablePayload");
  });
});

describe("G-PROXY-LIVE runtime (mutation: omit odds_mode or send live must fail)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchNflFairLines default GET sends odds_mode=skip", async () => {
    stubDummyOddsKeys();
    vi.resetModules();
    stubDummyOddsKeys();
    const { fetchNflFairLines } = await import("@/lib/nfl-fair-lines");
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const href = String(input);
      expect(href).toContain("/nfl/fair-lines");
      expect(href).toContain("odds_mode=skip");
      expect(href).not.toMatch(/odds_mode=live/);
      return new Response(
        JSON.stringify({
          season: 2026,
          count: 0,
          lines: [],
          diagnostics: { odds_mode: "skip" },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    await fetchNflFairLines({ season: 2026, daysAhead: 120 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("fetchNflFairLines({ oddsMode: live }) is coerced to skip", async () => {
    stubDummyOddsKeys();
    vi.resetModules();
    stubDummyOddsKeys();
    const { fetchNflFairLines } = await import("@/lib/nfl-fair-lines");
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      expect(String(input)).toContain("odds_mode=skip");
      return new Response(
        JSON.stringify({ season: 2026, count: 0, lines: [], diagnostics: {} }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    await fetchNflFairLines({
      season: 2026,
      oddsMode: "live",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("G-S6-CLIENT-SNAP runtime", () => {
  let probe: ReturnType<typeof installOddsHostFailOnHit>;

  beforeEach(async () => {
    stubDummyOddsKeys();
    vi.resetModules();
    stubDummyOddsKeys();
    probe = installOddsHostFailOnHit();
  });

  afterEach(() => {
    probe.restore();
  });

  it("POST with unsigned capturedAt=now + fake alts is researchOnly unavailable", async () => {
    const { POST } = await import("@/app/api/line-curve/route");
    const snap = {
      ...missouriOklahomaFixture.missouri.snapshot,
      capturedAt: new Date().toISOString(),
      source: "odds_api" as const,
    };
    const res = await POST(
      new Request("http://localhost/api/line-curve", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          eventId: snap.eventId,
          side: "Missouri",
          book: "draftkings",
          model: missouriOklahomaFixture.missouri.model,
          snapshot: snap,
        }),
      }),
    );
    const body = (await res.json()) as {
      researchOnly?: boolean;
      reason?: string;
      curve?: { ok?: boolean; points?: unknown[] };
    };
    expect(res.status).toBe(200);
    expect(body.researchOnly).toBe(true);
    expect(body.reason).toBe("alt_market_unavailable");
    expect(body.curve?.ok).toBe(false);
    expect(body.curve?.points).toBeUndefined();
    expect(probe.hits).toEqual([]);
  });
});

describe("G-NCAAM-PROXY runtime", () => {
  it("ncaam/today does not call Railway and returns paid_fetch_denied", async () => {
    stubDummyOddsKeys();
    delete process.env.INTERNAL_API_SECRET;
    vi.resetModules();
    stubDummyOddsKeys();
    delete process.env.INTERNAL_API_SECRET;
    const probe = installOddsHostFailOnHit();
    const fetchSpy = vi.fn(globalThis.fetch);
    vi.stubGlobal("fetch", fetchSpy);
    const { GET } = await import("@/app/api/edge-board/ncaam/today/route");
    const res = await GET(
      new Request("http://localhost/api/edge-board/ncaam/today"),
    );
    const body = (await res.json()) as { source?: string; reason?: string };
    expect([200, 401]).toContain(res.status);
    if (res.status === 200) {
      expect(body.source).toBe("none");
      expect(body.reason).toBe("paid_fetch_denied");
    }
    const railway = fetchSpy.mock.calls.filter((c) =>
      String(c[0]).includes("/edge-board/ncaam/today"),
    );
    expect(railway).toEqual([]);
    expect(probe.hits).toEqual([]);
    probe.restore();
    vi.unstubAllGlobals();
  });
});

describe("G-I3-STUB warm actually dispatches assemble", () => {
  it("I3: warm origin fetch runs assemble GET (not a dummy 200)", async () => {
    stubDummyOddsKeys();
    process.env.CRON_SECRET = "warm-secret";
    process.env.CFB_EDGE_BOARD_INTERNAL = "true";
    process.env.NFL_EDGE_BOARD_INTERNAL = "true";
    vi.resetModules();
    stubDummyOddsKeys();
    process.env.CRON_SECRET = "warm-secret";
    process.env.CFB_EDGE_BOARD_INTERNAL = "true";
    process.env.NFL_EDGE_BOARD_INTERNAL = "true";

    const { GET: assembleGET } =
      await import("@/app/api/edge-board/[sport]/assemble/route");
    const { GET: warmGET } =
      await import("@/app/api/cron/warm-page-data/route");
    const assembleHits: string[] = [];
    const oddsHits: string[] = [];
    const previous = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("the-odds-api.com")) {
        oddsHits.push(url);
        throw new Error(`ODDS_HOST_FAIL_ON_HIT ${url}`);
      }
      if (url.includes("/api/edge-board/") && url.includes("/assemble")) {
        assembleHits.push(url);
        const sport = url.includes("/cfb/") ? "cfb" : "nfl";
        return assembleGET(new Request(url), {
          params: Promise.resolve({ sport }),
        });
      }
      return new Response(JSON.stringify({ ok: true, rows: [], events: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }) as typeof fetch;

    const res = await warmGET(
      new Request("http://localhost/api/cron/warm-page-data", {
        headers: { authorization: "Bearer warm-secret" },
      }),
    );
    globalThis.fetch = previous;
    expect(res.status).toBe(200);
    expect(assembleHits.length).toBeGreaterThanOrEqual(1);
    expect(oddsHits).toEqual([]);
    delete process.env.CRON_SECRET;
    delete process.env.CFB_EDGE_BOARD_INTERNAL;
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    void DUMMY_ODDS_KEY;
  });
});
