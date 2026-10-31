import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DUMMY_ODDS_KEY,
  installOddsHostFailOnHit,
  stubDummyOddsKeys,
} from "@/__tests__/helpers/authorized-odds-job";
import {
  classifyAltSnapshot,
  resetLineCurveDegradeCounts,
} from "@/lib/line-curve/degrade";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(async () => "authorized"),
}));

// Keys must exist before the first `@/lib/config/env` parse in this file.
stubDummyOddsKeys();

function params(sport: string) {
  return { params: Promise.resolve({ sport }) };
}

function req(url: string, headers?: Record<string, string>) {
  return new Request(url, { headers });
}

type ISeriesMods = {
  compareGET: (typeof import("@/app/api/odds/[sport]/compare/route"))["GET"];
  todayGET: (typeof import("@/app/api/edge-board/[sport]/today/route"))["GET"];
  ncaamTodayGET: (typeof import("@/app/api/edge-board/ncaam/today/route"))["GET"];
  assembleGET: (typeof import("@/app/api/edge-board/[sport]/assemble/route"))["GET"];
  lineCurveGET: (typeof import("@/app/api/line-curve/route"))["GET"];
  lineCurvePOST: (typeof import("@/app/api/line-curve/route"))["POST"];
  lineCurveOptimizePOST: (typeof import("@/app/api/line-curve/optimize/route"))["POST"];
  widgetGET: (typeof import("@/app/api/odds-widget/[sport]/route"))["GET"];
  warmGET: (typeof import("@/app/api/cron/warm-page-data/route"))["GET"];
  loadAssembledEdgeBoardRows: (typeof import("@/lib/build-edge-board-rows"))["loadAssembledEdgeBoardRows"];
  loadCfbCurrentMarketRows: (typeof import("@/lib/cfb-edge-board-odds"))["loadCfbCurrentMarketRows"];
  loadCfbFuturesOdds: (typeof import("@/lib/cfb-futures-odds"))["loadCfbFuturesOdds"];
  loadNflFuturesOdds: (typeof import("@/lib/nfl-futures-odds"))["loadNflFuturesOdds"];
  fetchNflPreseasonOddsMarkets: (typeof import("@/lib/nfl-preseason-odds"))["fetchNflPreseasonOddsMarkets"];
  fetchAlternateSpreadSnapshot: (typeof import("@/lib/line-curve/odds-adapter"))["fetchAlternateSpreadSnapshot"];
  getOddsApiKeys: (typeof import("@/lib/odds-api-keys"))["getOddsApiKeys"];
  env: (typeof import("@/lib/config/env"))["env"];
};

/**
 * Re-parse env.ts after stubbing dummy keys. Static imports close over the
 * import-time Zod parse and make I-series vacuous (G-C7-VACUOUS / E6).
 */
async function loadISeriesModules(): Promise<ISeriesMods> {
  stubDummyOddsKeys();
  vi.resetModules();
  stubDummyOddsKeys();
  const [
    compare,
    today,
    ncaam,
    assemble,
    lineCurve,
    lineCurveOpt,
    widget,
    warm,
    assembleRows,
    cfbMarket,
    cfbFutures,
    nflFutures,
    preseason,
    adapter,
    keys,
    envMod,
  ] = await Promise.all([
    import("@/app/api/odds/[sport]/compare/route"),
    import("@/app/api/edge-board/[sport]/today/route"),
    import("@/app/api/edge-board/ncaam/today/route"),
    import("@/app/api/edge-board/[sport]/assemble/route"),
    import("@/app/api/line-curve/route"),
    import("@/app/api/line-curve/optimize/route"),
    import("@/app/api/odds-widget/[sport]/route"),
    import("@/app/api/cron/warm-page-data/route"),
    import("@/lib/build-edge-board-rows"),
    import("@/lib/cfb-edge-board-odds"),
    import("@/lib/cfb-futures-odds"),
    import("@/lib/nfl-futures-odds"),
    import("@/lib/nfl-preseason-odds"),
    import("@/lib/line-curve/odds-adapter"),
    import("@/lib/odds-api-keys"),
    import("@/lib/config/env"),
  ]);
  return {
    compareGET: compare.GET,
    todayGET: today.GET,
    ncaamTodayGET: ncaam.GET,
    assembleGET: assemble.GET,
    lineCurveGET: lineCurve.GET,
    lineCurvePOST: lineCurve.POST,
    lineCurveOptimizePOST: lineCurveOpt.POST,
    widgetGET: widget.GET,
    warmGET: warm.GET,
    loadAssembledEdgeBoardRows: assembleRows.loadAssembledEdgeBoardRows,
    loadCfbCurrentMarketRows: cfbMarket.loadCfbCurrentMarketRows,
    loadCfbFuturesOdds: cfbFutures.loadCfbFuturesOdds,
    loadNflFuturesOdds: nflFutures.loadNflFuturesOdds,
    fetchNflPreseasonOddsMarkets: preseason.fetchNflPreseasonOddsMarkets,
    fetchAlternateSpreadSnapshot: adapter.fetchAlternateSpreadSnapshot,
    getOddsApiKeys: keys.getOddsApiKeys,
    env: envMod.env,
  };
}

describe("I1/I2/I3/I5 request-path fail-closed (S1–S8)", () => {
  let probe: ReturnType<typeof installOddsHostFailOnHit>;
  let mods: ISeriesMods;

  beforeEach(async () => {
    stubDummyOddsKeys();
    delete process.env.ODDS_WEB_PAID_FETCH_ALLOW;
    delete process.env.REDIS_URL;
    resetLineCurveDegradeCounts();
    mods = await loadISeriesModules();
    probe = installOddsHostFailOnHit();
  });

  afterEach(() => {
    probe.restore();
    delete process.env.CFB_EDGE_BOARD_INTERNAL;
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.CRON_SECRET;
  });

  it("E6 harness: dummy keys parse into env before loaders (anti-vacuous)", () => {
    expect(mods.getOddsApiKeys()).toEqual([DUMMY_ODDS_KEY]);
    expect(mods.env.ODDS_API_KEY).toBe(DUMMY_ODDS_KEY);
    expect(mods.env.ODDS_WIDGET_ACCESS_KEY).toBe(DUMMY_ODDS_KEY);
    expect(process.env.ODDS_WEB_PAID_FETCH_ALLOW).not.toBe("1");
  });

  it("I5 S1: /api/odds/nba/compare cache miss returns none and 0 Odds hits", async () => {
    const res = await mods.compareGET(
      req("http://localhost/api/odds/nba/compare"),
      params("nba"),
    );
    const body = (await res.json()) as {
      source?: string;
      reason?: string;
      availability?: string;
    };
    expect(res.status).toBe(200);
    expect(body.source).toBe("none");
    expect(body.reason).toBe("paid_fetch_denied");
    expect(body.availability).toBe("unavailable");
    expect(probe.hits).toEqual([]);
  });

  it("I1 S1 fallback: compare still denies with spoofed warm headers", async () => {
    const res = await mods.compareGET(
      req("http://localhost/api/odds/mlb/compare", {
        "x-kosedge-warm": "1",
        "x-vercel-cron": "1",
      }),
      params("mlb"),
    );
    const body = (await res.json()) as { source?: string };
    expect(body.source).toBe("none");
    expect(probe.hits).toEqual([]);
  });

  it("I1 S2: edge-board today cache miss does not acquire", async () => {
    const res = await mods.todayGET(
      req("http://localhost/api/edge-board/nba/today"),
      params("nba"),
    );
    const body = (await res.json()) as { source?: string; reason?: string };
    expect([200, 401]).toContain(res.status);
    if (res.status === 200) {
      expect(body.source === "none" || body.source === "snapshot").toBe(true);
    }
    expect(probe.hits).toEqual([]);
  });

  it("I1 S3: ncaam/today has no Odds fallback", async () => {
    const res = await mods.ncaamTodayGET(
      req("http://localhost/api/edge-board/ncaam/today"),
    );
    const body = (await res.json()) as { source?: string; reason?: string };
    expect([200, 401]).toContain(res.status);
    if (res.status === 200) {
      expect(
        body.reason === "paid_fetch_denied" || body.source === "snapshot",
      ).toBe(true);
    }
    expect(probe.hits).toEqual([]);
  });

  it("I1 S4: assemble + loaders with football gate OPEN still 0 Odds hits", async () => {
    expect(mods.getOddsApiKeys()).toEqual([DUMMY_ODDS_KEY]);
    process.env.CFB_EDGE_BOARD_INTERNAL = "true";
    process.env.NFL_EDGE_BOARD_INTERNAL = "true";
    const cfb = await mods.assembleGET(
      req("http://localhost/api/edge-board/cfb/assemble"),
      params("cfb"),
    );
    const nba = await mods.assembleGET(
      req("http://localhost/api/edge-board/nba/assemble"),
      params("nba"),
    );
    expect(cfb.status).toBeGreaterThanOrEqual(200);
    expect(nba.status).toBeGreaterThanOrEqual(200);
    const market = await mods.loadCfbCurrentMarketRows({
      nowMs: Date.parse("2026-09-10T16:00:00Z"),
    });
    expect(market.source).not.toBe("vercel_live");
    await mods.loadAssembledEdgeBoardRows("nba").catch(() => undefined);
    await mods.loadAssembledEdgeBoardRows("nfl").catch(() => undefined);
    expect(probe.hits).toEqual([]);
  });

  it("I3 S5: warm-page-data with CRON_SECRET + dummy key + gate OPEN never acquires", async () => {
    process.env.CRON_SECRET = "warm-secret";
    process.env.CFB_EDGE_BOARD_INTERNAL = "true";
    process.env.NFL_EDGE_BOARD_INTERNAL = "true";
    const res = await mods.warmGET(
      req("http://localhost/api/cron/warm-page-data", {
        authorization: "Bearer warm-secret",
      }),
    );
    expect(res.status).toBe(200);
    const assemble = await mods.assembleGET(
      req("http://localhost/api/edge-board/cfb/assemble", {
        "x-kosedge-warm": "1",
      }),
      params("cfb"),
    );
    expect(assemble.status).toBeGreaterThanOrEqual(200);
    expect(probe.hits).toEqual([]);
  });

  it("I1 S6: line-curve GET/POST never live-pull", async () => {
    const get = await mods.lineCurveGET(req("http://localhost/api/line-curve"));
    const getBody = (await get.json()) as {
      researchOnly?: boolean;
      reason?: string;
    };
    expect(get.status).toBe(200);
    expect(getBody.researchOnly).toBe(true);
    expect(getBody.reason).toBe("alt_market_unavailable");

    const post = await mods.lineCurvePOST(
      new Request("http://localhost/api/line-curve", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          eventId: "evt",
          side: "Missouri",
          book: "draftkings",
          model: missouriOklahomaFixture.missouri.model,
        }),
      }),
    );
    const postBody = (await post.json()) as { reason?: string };
    expect(post.status).toBe(200);
    expect(postBody.reason).toBe("alt_market_unavailable");

    const opt = await mods.lineCurveOptimizePOST(
      new Request("http://localhost/api/line-curve/optimize", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      }),
    );
    const optBody = (await opt.json()) as { reason?: string };
    expect(opt.status).toBe(200);
    expect(optBody.reason).toBe("alt_market_unavailable");
    expect(probe.hits).toEqual([]);
  });

  it("I2 S7: Pro futures/slate loaders return unavailable and 0 Odds hits", async () => {
    expect(mods.getOddsApiKeys()).toEqual([DUMMY_ODDS_KEY]);
    const nfl = await mods.loadNflFuturesOdds();
    const cfb = await mods.loadCfbFuturesOdds();
    const pre = await mods.fetchNflPreseasonOddsMarkets();
    expect(nfl.status).toBe("unavailable");
    expect(cfb.status).toBe("unavailable");
    expect(pre.status).toBe("unavailable");
    expect(nfl.status).not.toBe("no_key");
    expect(cfb.status).not.toBe("no_key");
    expect(pre.status).not.toBe("no_key");
    expect(nfl.note).toMatch(/unavailable|as-of/i);
    expect(nfl.source).toBe("unavailable");
    expect(cfb.source).toBe("unavailable");
    expect(nfl.source).not.toBe("The Odds API");
    expect(cfb.source).not.toBe("The Odds API");
    expect(probe.hits).toEqual([]);
  });

  it("I1 S8: odds-widget is denied (404) with dummy key and 0 Odds hits", async () => {
    expect(mods.env.ODDS_WIDGET_ACCESS_KEY).toBe(DUMMY_ODDS_KEY);
    const res = await mods.widgetGET(
      req("http://localhost/api/odds-widget/nfl"),
      params("nfl"),
    );
    expect(res.status).toBe(404);
    expect(probe.hits).toEqual([]);
  });

  it("S6 live adapter on request path does not hit Odds", async () => {
    expect(mods.getOddsApiKeys()).toEqual([DUMMY_ODDS_KEY]);
    const closedSnap = await mods.fetchAlternateSpreadSnapshot({
      sport: "cfb",
      eventId: "evt-1",
      book: "draftkings",
    });
    expect(closedSnap).toMatchObject({
      ok: false,
      code: "unavailable_alt_market",
    });
    expect(probe.hits).toEqual([]);
  });
});

describe("L1 line-curve three-tier degrade (S6)", () => {
  it("classifies fresh / stale / none without outbound", () => {
    resetLineCurveDegradeCounts();
    const now = Date.parse("2026-09-11T01:10:00.000Z");
    const snap = missouriOklahomaFixture.missouri.snapshot;
    const fresh = classifyAltSnapshot(
      { ...snap, capturedAt: "2026-09-11T01:00:00.000Z" },
      now,
    );
    const stale = classifyAltSnapshot(
      { ...snap, capturedAt: "2026-09-10T12:00:00.000Z" },
      now,
    );
    const none = classifyAltSnapshot(null, now);
    expect(fresh.tier).toBe("fresh");
    expect(stale.tier).toBe("stale");
    expect(stale.label).toBe("STALE");
    expect(stale.optimizeDisabled).toBe(true);
    expect(none.tier).toBe("none");
    expect(none.reason).toBe("alt_market_unavailable");
    expect(none.label).toBe("Market alt prices unavailable");
  });
});
