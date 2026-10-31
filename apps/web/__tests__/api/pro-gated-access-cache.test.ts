import { beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";
import {
  isFootballPublicNumbersDisabled,
  NFL_EDGE_BOARD_PUBLIC_ENABLED,
} from "@/lib/cfb-edge-board-public";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(),
}));

vi.mock("@/lib/mlb-fair-lines", () => ({
  fetchMlbFairLines: vi.fn(),
}));
vi.mock("@/lib/nba-fair-lines", () => ({
  fetchNbaFairLines: vi.fn(),
}));
vi.mock("@/lib/nhl-fair-lines", () => ({
  fetchNhlFairLines: vi.fn(),
}));
vi.mock("@/lib/wnba-fair-lines", () => ({
  fetchWnbaFairLines: vi.fn(),
}));
vi.mock("@/lib/nfl-fair-lines", () => ({
  fetchNflFairLines: vi.fn(),
}));
vi.mock("@/lib/nfl-edges", () => ({
  fetchNflEdgesDesk: vi.fn(),
}));

import { getProAccessState } from "@/lib/auth/pro";
import { GET as getNflFair } from "@/app/api/nfl/fair-lines/route";
import { GET as getNcaafFair } from "@/app/api/ncaaf/fair-lines/route";
import { GET as getCfbFair } from "@/app/api/cfb/fair-lines/route";
import { GET as getMlbFair } from "@/app/api/mlb/fair-lines/route";
import { GET as getNbaFair } from "@/app/api/nba/fair-lines/route";
import { GET as getNhlFair } from "@/app/api/nhl/fair-lines/route";
import { GET as getWnbaFair } from "@/app/api/wnba/fair-lines/route";
import { GET as getEdgesDesk } from "@/app/api/nfl/edges-desk/route";
import {
  GET as getLineCurve,
  POST as postLineCurve,
} from "@/app/api/line-curve/route";
import { POST as postLineCurveOptimize } from "@/app/api/line-curve/optimize/route";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { fetchNbaFairLines } from "@/lib/nba-fair-lines";
import { fetchNhlFairLines } from "@/lib/nhl-fair-lines";
import { fetchWnbaFairLines } from "@/lib/wnba-fair-lines";

const NO_STORE = PAGE_DATA_NO_STORE;

type RouteCall = {
  name: string;
  call: () => Promise<Response>;
};

const req = (url: string, init?: RequestInit) => new Request(url, init);

const SECTION5_ROUTES: RouteCall[] = [
  {
    name: "GET /api/nfl/fair-lines",
    call: () => getNflFair(req("http://localhost/api/nfl/fair-lines")),
  },
  {
    name: "GET /api/ncaaf/fair-lines",
    call: () => getNcaafFair(),
  },
  {
    name: "GET /api/cfb/fair-lines",
    call: () => getCfbFair(),
  },
  {
    name: "GET /api/mlb/fair-lines",
    call: () => getMlbFair(req("http://localhost/api/mlb/fair-lines")),
  },
  {
    name: "GET /api/nba/fair-lines",
    call: () => getNbaFair(req("http://localhost/api/nba/fair-lines")),
  },
  {
    name: "GET /api/nhl/fair-lines",
    call: () => getNhlFair(req("http://localhost/api/nhl/fair-lines")),
  },
  {
    name: "GET /api/wnba/fair-lines",
    call: () => getWnbaFair(req("http://localhost/api/wnba/fair-lines")),
  },
  {
    name: "GET /api/nfl/edges-desk",
    call: () => getEdgesDesk(req("http://localhost/api/nfl/edges-desk")),
  },
  {
    name: "GET /api/line-curve",
    call: () => getLineCurve(req("http://localhost/api/line-curve")),
  },
  {
    name: "POST /api/line-curve",
    call: () =>
      postLineCurve(
        req("http://localhost/api/line-curve", {
          method: "POST",
          body: "{}",
        }),
      ),
  },
  {
    name: "POST /api/line-curve/optimize",
    call: () =>
      postLineCurveOptimize(
        req("http://localhost/api/line-curve/optimize", {
          method: "POST",
          body: "{}",
        }),
      ),
  },
];

const PRO_CACHE_ROUTES: RouteCall[] = SECTION5_ROUTES.filter((r) =>
  /fair-lines|edges-desk/.test(r.name),
);

function expectNoStore(res: Response) {
  expect(res.headers.get("Cache-Control")).toBe(NO_STORE);
  expect(res.headers.get("CDN-Cache-Control")).toBe(NO_STORE);
  expect(res.headers.get("Cache-Control")).not.toContain("public");
  expect(res.headers.get("Cache-Control")).not.toContain("s-maxage");
}

function emptyBoard() {
  return {
    gameDate: "2026-09-04",
    modelVersion: "",
    workerBuildId: "",
    count: 0,
    lines: [],
    slateStatus: "no_slate" as const,
    message: "empty",
  };
}

function occupiedNbaBoard() {
  return {
    gameDate: "2026-09-04",
    modelVersion: "nba-test",
    workerBuildId: "w1",
    count: 1,
    lines: [
      {
        gameId: "g1",
        gameDate: "2026-09-04",
        startTime: null,
        homeTeam: "Home",
        awayTeam: "Away",
        homeWinProb: 0.55,
        fairHomeMl: -120,
        fairAwayMl: 100,
        totalMean: 220,
        fairTotal: 220,
        fairSpreadHome: -3.5,
        homeCoverProb: 0.52,
        marginMean: 3.1,
        projectedAt: null,
        modelVersion: "nba-test",
        workerBuildId: "w1",
      },
    ],
    slateStatus: "ok" as const,
    message: "ok",
  };
}

describe("Pro-gated APIs — 401 + private cache (A4/A6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchMlbFairLines).mockResolvedValue(emptyBoard());
    vi.mocked(fetchNbaFairLines).mockResolvedValue(occupiedNbaBoard());
    vi.mocked(fetchNhlFairLines).mockResolvedValue(emptyBoard());
    vi.mocked(fetchWnbaFairLines).mockResolvedValue(emptyBoard());
  });

  it("every §5 API returns 401 private,no-store when unauthenticated", async () => {
    vi.mocked(getProAccessState).mockResolvedValue("unauthenticated");
    for (const route of SECTION5_ROUTES) {
      const res = await route.call();
      expect(res.status, route.name).toBe(401);
      expectNoStore(res);
    }
  });

  it("unauth after an entitled authorized 200 gets 401, not a stale shared 200", async () => {
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
    const entitled = await getNbaFair(
      req("http://localhost/api/nba/fair-lines"),
    );
    expect(entitled.status).toBe(200);
    expectNoStore(entitled);
    const entitledBody = (await entitled.json()) as { count?: number };
    expect(entitledBody.count).toBe(1);

    vi.mocked(getProAccessState).mockResolvedValue("unauthenticated");
    const unauth = await getNbaFair(
      req("http://localhost/api/nba/fair-lines"),
    );
    expect(unauth.status).toBe(401);
    expectNoStore(unauth);
    const unauthBody = (await unauth.json()) as { error?: string };
    expect(unauthBody.error).toBe("Unauthorized");
    expect(unauth.headers.get("Cache-Control")).not.toContain("public");
  });

  it("all 7 fair-lines + edges-desk authorized bodies are private,no-store", async () => {
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
    for (const route of PRO_CACHE_ROUTES) {
      const res = await route.call();
      expect([200, 503], route.name).toContain(res.status);
      expectNoStore(res);
    }
  });

  it("FB-kill holds for authorized admin even when preview would be true (A5)", async () => {
    expect(NFL_EDGE_BOARD_PUBLIC_ENABLED).toBe(false);
    expect(isFootballPublicNumbersDisabled("nfl")).toBe(true);
    expect(isFootballPublicNumbersDisabled("cfb")).toBe(true);

    vi.mocked(getProAccessState).mockResolvedValue("authorized");
    const edges = await getEdgesDesk(
      req("http://localhost/api/nfl/edges-desk"),
    );
    expect(edges.status).toBe(503);
    expectNoStore(edges);
    const edgesBody = (await edges.json()) as { error?: string };
    expect(edgesBody.error).toBe("nfl_edge_board_unavailable");

    const fair = await getNflFair(req("http://localhost/api/nfl/fair-lines"));
    expect(fair.status).toBe(503);
    expectNoStore(fair);

    const pub = readFileSync(
      path.join(process.cwd(), "lib/cfb-edge-board-public.ts"),
      "utf8",
    );
    expect(pub).toContain("NFL_EDGE_BOARD_PUBLIC_ENABLED = false");
    expect(pub).toContain("CFB_EDGE_BOARD_PUBLIC_ENABLED = false");
  });
});
