/**
 * WEB_OWNED_ONLY_R1 — B independent helper/route + integration (CERT=0).
 * OWNER CLEAR 85a714cd · Cos LAUNCH 032a4de7 · B ORDER 1f9256c7.
 *
 * Mocked / synthetic only. No live Odds API, network, DB, job, simulator,
 * or outcome calls. No access flip. No collector/scheduler edits.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import {
  fetchNflFairLines,
  NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED,
  NFL_FAIR_LINES_REUSE_UNAVAILABLE,
  NflFairLinesUnavailableError,
} from "@/lib/nfl-fair-lines";
import {
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
  isNflFairLinesCustomerSurfaceClosed,
} from "@/lib/cfb-edge-board-public";
import {
  UpstreamTimeoutError,
  UPSTREAM_TIMEOUT_MS,
} from "@/lib/upstream-fetch";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(),
}));

import { getProAccessState } from "@/lib/auth/pro";
import { GET as getNflFairLines } from "@/app/api/nfl/fair-lines/route";

const root = process.cwd();
const ALLOWED_UPSTREAM_PREFIX = "http://localhost:8000/nfl/fair-lines";
const FORBIDDEN_HOST_RE =
  /the-odds-api\.com|widget\.the-odds-api\.com|railway\.app|kosedge\.com/;

type LedgerEntry = {
  href: string;
  method: string;
  body: unknown;
};

const ledger: LedgerEntry[] = [];

type FairParams = Parameters<typeof fetchNflFairLines>[0];

function readApp(rel: string): string {
  return readFileSync(path.join(root, rel), "utf8");
}

function okBoard(overrides: Record<string, unknown> = {}) {
  return {
    season: 2026,
    model_version: "owned-only-synthetic",
    count: 0,
    lines: [],
    window: { days_ahead: 14, include_past_days: 0 },
    diagnostics: {
      odds_mode: "skip",
      odds_feed_status: "skipped",
      odds_events_seen: 0,
      market_joined_count: 0,
      bookmakers: [],
      kosedge_only: true,
      odds_persisted: {
        events_persisted: 0,
        snapshots_inserted: 0,
        history_upserted: 0,
      },
    },
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function installFetchMock(
  impl?: (href: string, init?: RequestInit) => Response | Promise<Response>,
) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const href = String(input);
      if (
        FORBIDDEN_HOST_RE.test(href) ||
        !href.startsWith("http://localhost:8000/")
      ) {
        throw new Error(`FORBIDDEN_UPSTREAM: ${href}`);
      }
      let body: unknown;
      if (typeof init?.body === "string") {
        try {
          body = JSON.parse(init.body);
        } catch {
          body = init.body;
        }
      }
      ledger.push({
        href,
        method: String(init?.method || "GET").toUpperCase(),
        body,
      });
      if (impl) return impl(href, init);
      return jsonResponse(okBoard());
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function expectSyntheticOnly(entry: LedgerEntry) {
  expect(entry.href.startsWith(ALLOWED_UPSTREAM_PREFIX)).toBe(true);
  expect(FORBIDDEN_HOST_RE.test(entry.href)).toBe(false);
  expect(entry.href).not.toMatch(/odds_mode=live/);
}

function expectSkipGet(href: string, init?: RequestInit) {
  expect(href).toContain("/nfl/fair-lines");
  expect(href).toContain("persist=0");
  expect(href).not.toMatch(/persist=1/);
  expect(href).toContain("odds_mode=skip");
  expect(href).not.toMatch(/odds_mode=live/);
  expect(String(init?.method || "GET").toUpperCase()).toBe("GET");
}

function expectReusePost(href: string, init?: RequestInit) {
  expect(href).toContain("/nfl/fair-lines");
  expect(href).toContain("persist=0");
  expect(href).toContain("odds_mode=reuse");
  expect(href).not.toMatch(/persist=1/);
  expect(href).not.toMatch(/odds_mode=live/);
  expect(String(init?.method || "GET").toUpperCase()).toBe("POST");
  const body = JSON.parse(String(init?.body || "{}")) as {
    odds_mode?: string;
    persist?: unknown;
    odds_events?: unknown;
    odds_payload?: unknown;
  };
  expect(body.odds_mode).toBe("reuse");
  expect(body.persist).toBe(0);
  expect(body.odds_mode).not.toBe("live");
  return body;
}

async function expectOwnedRefusal(
  run: () => Promise<unknown>,
  fetchMock: ReturnType<typeof vi.fn>,
  message: string,
) {
  const before = fetchMock.mock.calls.length;
  let thrown: unknown;
  let result: unknown;
  try {
    result = await run();
  } catch (err) {
    thrown = err;
  }
  expect(
    fetchMock.mock.calls.length,
    "ZERO upstream on owned-only refuse",
  ).toBe(before);
  if (thrown) {
    expect(thrown).toBeInstanceOf(NflFairLinesUnavailableError);
    expect((thrown as Error).message).toBe(message);
    return;
  }
  const board = result as {
    count?: number;
    lines?: unknown[];
    error?: string;
    oddsAsOf?: string | null;
  };
  expect(board.count).toBe(0);
  expect(board.lines).toEqual([]);
  expect(board.oddsAsOf ?? null).toBeNull();
  expect(board.error).toBe(message);
}

function asFairParams(params: Record<string, unknown>): FairParams {
  return params as FairParams;
}

function fairRequest(url = "http://localhost/api/nfl/fair-lines"): Request {
  return new Request(url);
}

function expectNoStore(res: Response) {
  expect(res.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  expect(res.headers.get("CDN-Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  expect(res.headers.get("Cache-Control")).not.toContain("public");
  expect(res.headers.get("Cache-Control")).not.toContain("s-maxage");
}

describe("WEB_OWNED_ONLY_R1 fetchNflFairLines + /api/nfl/fair-lines", () => {
  beforeEach(() => {
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
  });

  afterEach(() => {
    for (const entry of ledger) {
      expectSyntheticOnly(entry);
    }
    delete process.env.NFL_EDGE_BOARD_INTERNAL;
    delete process.env.NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL;
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("1) default → skip URL + persist=0 (no live inherit)", async () => {
    const fetchMock = installFetchMock(() => jsonResponse(okBoard()));

    const board = await fetchNflFairLines({ season: 2026 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const href = String(fetchMock.mock.calls[0]?.[0]);
    expectSkipGet(href, fetchMock.mock.calls[0]?.[1]);
    expect(board.count).toBe(0);
    expect(board.diagnostics.oddsPersisted).toEqual({
      eventsPersisted: 0,
      snapshotsInserted: 0,
      historyUpserted: 0,
    });
  });

  it("2a) explicit oddsMode=live → refusal + ZERO upstream", async () => {
    const fetchMock = installFetchMock();
    await expectOwnedRefusal(
      () => fetchNflFairLines(asFairParams({ season: 2026, oddsMode: "live" })),
      fetchMock,
      NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED,
    );
  });

  it("2b) explicit persistOdds=true → refusal + ZERO upstream", async () => {
    const fetchMock = installFetchMock();
    await expectOwnedRefusal(
      () => fetchNflFairLines({ season: 2026, persistOdds: true }),
      fetchMock,
      NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED,
    );
  });

  it("2c) live + persisttrue still never reaches upstream", async () => {
    const fetchMock = installFetchMock();
    await expectOwnedRefusal(
      () =>
        fetchNflFairLines(
          asFairParams({
            season: 2026,
            oddsMode: "live",
            persistOdds: true,
            throwOnTransportError: true,
          }),
        ),
      fetchMock,
      NFL_FAIR_LINES_PAID_ACQUISITION_REFUSED,
    );
  });

  it("3) valid owned reuse POST → no live fallback", async () => {
    const fetchMock = installFetchMock((href, init) => {
      const body = expectReusePost(href, init);
      expect(Array.isArray(body.odds_events)).toBe(true);
      expect((body.odds_events as unknown[]).length).toBeGreaterThan(0);
      expect(Array.isArray(body.odds_payload)).toBe(true);
      expect((body.odds_payload as unknown[]).length).toBeGreaterThan(0);
      return jsonResponse(
        okBoard({
          diagnostics: {
            odds_mode: "reuse",
            odds_feed_status: "skipped",
            odds_persisted: {
              events_persisted: 0,
              snapshots_inserted: 0,
              history_upserted: 0,
            },
          },
        }),
      );
    });

    await fetchNflFairLines({
      season: 2026,
      oddsMode: "reuse",
      oddsEvents: [
        {
          id: "syn-evt-1",
          home_team: "Seattle Seahawks",
          away_team: "New England Patriots",
          bookmakers: [],
        },
      ],
      oddsPayload: [{ game: "NE @ SEA", market: "Spread", line: -3 }],
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const href = String(fetchMock.mock.calls[0]?.[0]);
    expect(href).not.toMatch(/odds_mode=live/);
    expect(String(fetchMock.mock.calls[0]?.[1]?.method).toUpperCase()).toBe(
      "POST",
    );
  });

  it("4a) empty reuse → refuse before upstream", async () => {
    const fetchMock = installFetchMock();
    await expectOwnedRefusal(
      () =>
        fetchNflFairLines({
          season: 2026,
          oddsMode: "reuse",
          oddsEvents: [],
          oddsPayload: [],
        }),
      fetchMock,
      NFL_FAIR_LINES_REUSE_UNAVAILABLE,
    );
  });

  it("4b) missing reuse payload → refuse before upstream", async () => {
    const fetchMock = installFetchMock();
    await expectOwnedRefusal(
      () => fetchNflFairLines({ season: 2026, oddsMode: "reuse" }),
      fetchMock,
      NFL_FAIR_LINES_REUSE_UNAVAILABLE,
    );
  });

  it("4c) malformed reuse (non-array / null) → refuse before upstream", async () => {
    const fetchMock = installFetchMock();
    for (const bad of [
      { oddsEvents: "not-an-array" },
      { oddsPayload: { game: "NE @ SEA" } },
      { oddsEvents: null },
      { oddsPayload: 12 },
    ]) {
      await expectOwnedRefusal(
        () =>
          fetchNflFairLines(
            asFairParams({ season: 2026, oddsMode: "reuse", ...bad }),
          ),
        fetchMock,
        NFL_FAIR_LINES_REUSE_UNAVAILABLE,
      );
    }
  });

  it("5) authorized closed route → 503 + zero upstream", async () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isNflFairLinesCustomerSurfaceClosed()).toBe(true);
    const fetchMock = installFetchMock();

    const res = await getNflFairLines(fairRequest());
    expect(res.status).toBe(503);
    expectNoStore(res);
    const body = (await res.json()) as { error?: string };
    expect(body.error).toBe("nfl_edge_board_unavailable");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("6a) existing 401 private,no-store remains (zero upstream)", async () => {
    vi.mocked(getProAccessState).mockResolvedValue("unauthenticated");
    const fetchMock = installFetchMock();

    const res = await getNflFairLines(fairRequest());
    expect(res.status).toBe(401);
    expectNoStore(res);
    const body = (await res.json()) as { error?: string };
    expect(body.error).toBe("Unauthorized");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("6b) existing timeout → 504 private,no-store remains", async () => {
    const timedOut = pageDataUpstreamErrorResponse(
      new UpstreamTimeoutError(25_000, "http://localhost:8000/nfl/fair-lines"),
    );
    expect(timedOut.status).toBe(504);
    expectNoStore(timedOut);
    const body = (await timedOut.json()) as { error?: string };
    expect(body.error).toMatch(/timed out/i);
    expect(body).not.toHaveProperty("count");
    expect(body).not.toHaveProperty("oddsAsOf");
  });

  it("6c) existing transport 503 + helper throwOnTransportError remains", async () => {
    const unreachable = pageDataUpstreamErrorResponse(
      new Error("Unable to reach model service."),
    );
    expect(unreachable.status).toBe(503);
    expectNoStore(unreachable);

    const fetchMock = installFetchMock(() =>
      jsonResponse({ error: "upstream down" }, 503),
    );
    await expect(
      fetchNflFairLines({
        season: 2026,
        oddsMode: "skip",
        throwOnTransportError: true,
      }),
    ).rejects.toThrow(/Model service returned 503/);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expectSkipGet(
      String(fetchMock.mock.calls[0]?.[0]),
      fetchMock.mock.calls[0]?.[1],
    );
  });

  it("6d) helper timeout still throws on page-data path (skip, persist=0)", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(
      (_url: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          const href = String(_url);
          if (!href.startsWith("http://localhost:8000/")) {
            reject(new Error(`FORBIDDEN_UPSTREAM: ${href}`));
            return;
          }
          ledger.push({
            href,
            method: String(init?.method || "GET").toUpperCase(),
            body: undefined,
          });
          const signal = init?.signal;
          if (!signal) return;
          signal.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const pending = fetchNflFairLines({
      season: 2026,
      oddsMode: "skip",
      timeoutMs: 50,
      throwOnTransportError: true,
    });
    const assertion =
      expect(pending).rejects.toBeInstanceOf(UpstreamTimeoutError);
    await vi.advanceTimersByTimeAsync(60);
    await assertion;
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expectSkipGet(
      String(fetchMock.mock.calls[0]?.[0]),
      fetchMock.mock.calls[0]?.[1],
    );
  });

  it("integration: authorized QA path uses helper default skip + persist=0", async () => {
    // Documented INTERNAL QA override — not a public-flag access flip.
    process.env.NFL_EDGE_BOARD_INTERNAL = "1";
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isNflFairLinesCustomerSurfaceClosed()).toBe(false);
    const fetchMock = installFetchMock(() =>
      jsonResponse(
        okBoard({
          count: 1,
          lines: [
            {
              game_id: "syn-g1",
              home_team: "SEA",
              away_team: "NE",
              week: 1,
            },
          ],
        }),
      ),
    );

    const res = await getNflFairLines(fairRequest());
    expect(res.status, await res.clone().text()).toBe(200);
    expectNoStore(res);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expectSkipGet(
      String(fetchMock.mock.calls[0]?.[0]),
      fetchMock.mock.calls[0]?.[1],
    );
    const body = (await res.json()) as { count?: number };
    expect(body.count).toBe(1);
  });

  it("source-lock: route stays privateJson / persist0 / no live caller", () => {
    const route = readApp("app/api/nfl/fair-lines/route.ts");
    expect(route).toContain("pageDataPrivateJsonResponse");
    expect(route).toContain("persistOdds: false");
    expect(route).toContain("throwOnTransportError: true");
    expect(route).toContain("pageDataUpstreamErrorResponse");
    expect(route).toContain("isNflFairLinesCustomerSurfaceClosed");
    expect(route).not.toMatch(/oddsMode:\s*["']live["']/);
    expect(route).not.toContain("persistOdds: true");
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(UPSTREAM_TIMEOUT_MS.pageData).toBe(25_000);

    const callers = [
      "app/api/nfl/fair-lines/route.ts",
      "app/api/nfl/season-engine/survivor/route.ts",
      "app/api/nfl/season-engine/survivor/plan/route.ts",
      "app/(pro)/pro/nfl/fantasy/pickem/page.tsx",
      "app/(pro)/pro/prediction-market/page.tsx",
      "app/(pro)/pro/[sport]/execution/page.tsx",
      "lib/nfl-edges.ts",
      "lib/nfl-slate.ts",
      "lib/build-edge-board-rows.ts",
      "lib/resolve-kei-lines.ts",
      "lib/nfl-season-engine.ts",
    ];
    for (const rel of callers) {
      const src = readApp(rel);
      expect(src, rel).not.toMatch(/oddsMode:\s*["']live["']/);
      expect(src, rel).not.toContain("persistOdds: true");
    }
  });

  it("source-lock: helper default is skip (owned-only, no live inherit)", () => {
    const helper = readApp("lib/nfl-fair-lines.ts");
    expect(helper).not.toMatch(/oddsMode = params\.oddsMode \?\? ["']live["']/);
    expect(helper).toMatch(/oddsMode = params\.oddsMode \?\? ["']skip["']/);
  });

  it("receipt: suite is synthetic-only (no odds-client/network/DB/job/simulator/outcome)", () => {
    const self = readFileSync(
      path.join(root, "__tests__/lib/nfl-fair-lines-owned-only-r1.test.ts"),
      "utf8",
    );
    expect(self).not.toMatch(/from ["']@\/lib\/odds-api["']/);
    expect(self).not.toMatch(/from ["']@\/lib\/odds-api-keys["']/);
    expect(self).not.toMatch(/from ["']@\/lib\/nfl-preseason-odds["']/);
    expect(self).not.toMatch(/from ["']@\/lib\/nfl-futures-odds["']/);
    expect(self).not.toMatch(/from ["']@\/lib\/db["']/);
    expect(self).not.toMatch(/from ["']#prisma["']/);
    expect(
      ledger.every((e) => e.href.startsWith(ALLOWED_UPSTREAM_PREFIX)),
    ).toBe(true);
    expect(ledger.some((e) => FORBIDDEN_HOST_RE.test(e.href))).toBe(false);
  });
});
