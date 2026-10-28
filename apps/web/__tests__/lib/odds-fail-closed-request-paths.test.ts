import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installOddsHostFailOnHit } from "@/__tests__/helpers/authorized-odds-job";
import { GET as compareGET } from "@/app/api/odds/[sport]/compare/route";
import { GET as todayGET } from "@/app/api/edge-board/[sport]/today/route";
import { GET as ncaamTodayGET } from "@/app/api/edge-board/ncaam/today/route";
import { GET as assembleGET } from "@/app/api/edge-board/[sport]/assemble/route";
import {
  GET as lineCurveGET,
  POST as lineCurvePOST,
} from "@/app/api/line-curve/route";
import { POST as lineCurveOptimizePOST } from "@/app/api/line-curve/optimize/route";
import { GET as widgetGET } from "@/app/api/odds-widget/[sport]/route";
import { GET as warmGET } from "@/app/api/cron/warm-page-data/route";
import { loadAssembledEdgeBoardRows } from "@/lib/build-edge-board-rows";
import { loadCfbCurrentMarketRows } from "@/lib/cfb-edge-board-odds";
import { loadCfbFuturesOdds } from "@/lib/cfb-futures-odds";
import { loadNflFuturesOdds } from "@/lib/nfl-futures-odds";
import { fetchNflPreseasonOddsMarkets } from "@/lib/nfl-preseason-odds";
import { fetchAlternateSpreadSnapshot } from "@/lib/line-curve/odds-adapter";
import {
  classifyAltSnapshot,
  resetLineCurveDegradeCounts,
} from "@/lib/line-curve/degrade";
import { missouriOklahomaFixture } from "@/lib/line-curve/fixtures/missouri-oklahoma";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(async () => "authorized"),
}));

const dummyKey = "dummy-odds-key-t4662u";

function params(sport: string) {
  return { params: Promise.resolve({ sport }) };
}

function req(url: string, headers?: Record<string, string>) {
  return new Request(url, { headers });
}

describe("I1/I2/I3/I5 request-path fail-closed (S1–S8)", () => {
  let probe: ReturnType<typeof installOddsHostFailOnHit>;

  beforeEach(() => {
    probe = installOddsHostFailOnHit();
    process.env.ODDS_API_KEY = dummyKey;
    process.env.ODDS_API_KEY_BACKUP = dummyKey;
    process.env.ODDS_WIDGET_ACCESS_KEY = dummyKey;
    delete process.env.ODDS_WEB_PAID_FETCH_ALLOW;
    delete process.env.REDIS_URL;
    resetLineCurveDegradeCounts();
  });

  afterEach(() => {
    probe.restore();
    delete process.env.ODDS_API_KEY;
    delete process.env.ODDS_API_KEY_BACKUP;
    delete process.env.ODDS_WIDGET_ACCESS_KEY;
    delete process.env.CFB_EDGE_BOARD_INTERNAL;
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.CRON_SECRET;
  });

  it("I5 S1: /api/odds/nba/compare cache miss returns none and 0 Odds hits", async () => {
    const res = await compareGET(
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
    const res = await compareGET(
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
    const res = await todayGET(
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
    const res = await ncaamTodayGET(
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
    process.env.CFB_EDGE_BOARD_INTERNAL = "true";
    process.env.NFL_EDGE_BOARD_INTERNAL = "true";
    const cfb = await assembleGET(
      req("http://localhost/api/edge-board/cfb/assemble"),
      params("cfb"),
    );
    const nba = await assembleGET(
      req("http://localhost/api/edge-board/nba/assemble"),
      params("nba"),
    );
    expect(cfb.status).toBeGreaterThanOrEqual(200);
    expect(nba.status).toBeGreaterThanOrEqual(200);
    const market = await loadCfbCurrentMarketRows({
      nowMs: Date.parse("2026-09-10T16:00:00Z"),
    });
    expect(market.source).not.toBe("vercel_live");
    await loadAssembledEdgeBoardRows("nba").catch(() => undefined);
    expect(probe.hits).toEqual([]);
  });

  it("I3 S5: warm-page-data with CRON_SECRET + dummy key + gate OPEN never acquires", async () => {
    process.env.CRON_SECRET = "warm-secret";
    process.env.CFB_EDGE_BOARD_INTERNAL = "true";
    process.env.NFL_EDGE_BOARD_INTERNAL = "true";
    const res = await warmGET(
      req("http://localhost/api/cron/warm-page-data", {
        authorization: "Bearer warm-secret",
      }),
    );
    expect(res.status).toBe(200);
    const assemble = await assembleGET(
      req("http://localhost/api/edge-board/cfb/assemble", {
        "x-kosedge-warm": "1",
      }),
      params("cfb"),
    );
    expect(assemble.status).toBeGreaterThanOrEqual(200);
    expect(probe.hits).toEqual([]);
  });

  it("I1 S6: line-curve GET/POST never live-pull", async () => {
    const get = await lineCurveGET(req("http://localhost/api/line-curve"));
    const getBody = (await get.json()) as {
      researchOnly?: boolean;
      reason?: string;
    };
    expect(get.status).toBe(200);
    expect(getBody.researchOnly).toBe(true);
    expect(getBody.reason).toBe("alt_market_unavailable");

    const post = await lineCurvePOST(
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

    const opt = await lineCurveOptimizePOST(
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
    const nfl = await loadNflFuturesOdds();
    const cfb = await loadCfbFuturesOdds();
    const pre = await fetchNflPreseasonOddsMarkets();
    expect(nfl.status === "unavailable" || nfl.status === "no_key").toBe(true);
    expect(cfb.status === "unavailable" || cfb.status === "no_key").toBe(true);
    expect(pre.status === "unavailable" || pre.status === "no_key").toBe(true);
    expect(nfl.note).toMatch(/unavailable|as-of|—/i);
    expect(probe.hits).toEqual([]);
  });

  it("I1 S8: odds-widget is denied (404) with dummy key and 0 Odds hits", async () => {
    const res = await widgetGET(
      req("http://localhost/api/odds-widget/nfl"),
      params("nfl"),
    );
    expect(res.status).toBe(404);
    expect(probe.hits).toEqual([]);
  });

  it("S6 live adapter on request path does not hit Odds", async () => {
    const closedSnap = await fetchAlternateSpreadSnapshot({
      sport: "cfb",
      eventId: "evt-1",
      book: "draftkings",
    });
    expect("ok" in closedSnap && closedSnap.ok === false).toBe(true);
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
