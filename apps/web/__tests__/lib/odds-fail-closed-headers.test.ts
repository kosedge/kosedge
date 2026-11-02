import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import {
  installOddsHostFailOnHit,
  stubDummyOddsKeys,
} from "@/__tests__/helpers/authorized-odds-job";
import { rateLimit } from "@/lib/security/rate-limit";
import { GET as compareGET } from "@/app/api/odds/[sport]/compare/route";

stubDummyOddsKeys();

describe("I4/I6 spoofed cron/warm headers (S5)", () => {
  const prevSecret = process.env.CRON_SECRET;
  let probe: ReturnType<typeof installOddsHostFailOnHit>;

  beforeEach(() => {
    stubDummyOddsKeys();
    process.env.CRON_SECRET = "real-cron-secret";
    delete process.env.ODDS_WEB_PAID_FETCH_ALLOW;
    probe = installOddsHostFailOnHit();
  });

  afterEach(() => {
    probe.restore();
    if (prevSecret == null) delete process.env.CRON_SECRET;
    else process.env.CRON_SECRET = prevSecret;
    delete process.env.ODDS_API_KEY;
  });

  it("I4: spoofed x-kosedge-warm:1 without secret is rate-limited and 0 Odds hits", async () => {
    const ip = "spoof-warm-" + Date.now();
    const headers = {
      "x-forwarded-for": ip,
      "x-kosedge-warm": "1",
    };
    for (let i = 0; i < 10; i += 1) {
      const allowed = await rateLimit(
        new NextRequest("http://localhost/api/edge-board/nba/today", {
          headers,
        }),
      );
      expect(allowed).toBeNull();
    }
    const limited = await rateLimit(
      new NextRequest("http://localhost/api/edge-board/nba/today", {
        headers,
      }),
    );
    expect(limited?.status).toBe(429);

    const compare = await compareGET(
      new Request("http://localhost/api/odds/nba/compare", { headers }),
      { params: Promise.resolve({ sport: "nba" }) },
    );
    const body = (await compare.json()) as { source?: string };
    expect(body.source).toBe("none");
    expect(probe.hits).toEqual([]);
  });

  it("I6: spoofed x-vercel-cron:1 without secret is rate-limited and 0 Odds hits", async () => {
    const ip = "spoof-vercel-cron-" + Date.now();
    const headers = {
      "x-forwarded-for": ip,
      "x-vercel-cron": "1",
    };
    for (let i = 0; i < 10; i += 1) {
      const allowed = await rateLimit(
        new NextRequest("http://localhost/api/edge-board/nhl/today", {
          headers,
        }),
      );
      expect(allowed).toBeNull();
    }
    const limited = await rateLimit(
      new NextRequest("http://localhost/api/edge-board/nhl/today", {
        headers,
      }),
    );
    expect(limited?.status).toBe(429);

    const compare = await compareGET(
      new Request("http://localhost/api/odds/wnba/compare", { headers }),
      { params: Promise.resolve({ sport: "wnba" }) },
    );
    const body = (await compare.json()) as { source?: string };
    expect(body.source).toBe("none");
    expect(probe.hits).toEqual([]);
  });

  it("verified Bearer CRON_SECRET still exempts the limiter (not acquisition)", async () => {
    const ip = "verified-cron-" + Date.now();
    for (let i = 0; i < 12; i += 1) {
      const res = await rateLimit(
        new NextRequest("http://localhost/api/edge-board/nba/today", {
          headers: {
            "x-forwarded-for": ip,
            authorization: "Bearer real-cron-secret",
          },
        }),
      );
      expect(res).toBeNull();
    }
    expect(probe.hits).toEqual([]);
  });
});
