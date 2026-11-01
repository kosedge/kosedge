/**
 * T6-API-C10-CONSUMER-REFUSE — EXISTING BUT UNVERIFIED → route-level evidence.
 *
 * Lineage: eight-target #6 (fail closed on missing/invalid data) ·
 * ACCESS_MATRIX G1 consumer APIs · E1 FAIL_CLOSED C10/model unreachable.
 *
 * G1 A4 (private,no-store / no cross-user share) is sealed PASS (#676 /
 * 29b536b1) and is not re-opened here. FB-kill 503 is a different gate;
 * this file turns that kill OFF so the C10 path is actually exercised.
 *
 * Reuses G1 fixtures: getProAccessState mock, PAGE_DATA_NO_STORE,
 * pageDataUpstreamErrorResponse contract (no invented lines/rows/count).
 * No live Odds HTTP. No env secret reads. No new policy thresholds.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";
import { UpstreamTimeoutError } from "@/lib/upstream-fetch";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(),
}));

vi.mock("@/lib/nfl-fair-lines", () => ({
  fetchNflFairLines: vi.fn(),
}));

vi.mock("@/lib/nfl-edges", () => ({
  fetchNflEdgesDesk: vi.fn(),
}));

vi.mock("@/lib/build-edge-board-rows", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/build-edge-board-rows")>();
  return {
    ...actual,
    loadAssembledEdgeBoardRows: vi.fn(),
  };
});

vi.mock("@/lib/cfb-edge-board-public", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/cfb-edge-board-public")>();
  return {
    ...actual,
    isFootballPublicNumbersDisabled: vi.fn(() => false),
    isNflFairLinesCustomerSurfaceClosed: vi.fn(() => false),
  };
});

import { getProAccessState } from "@/lib/auth/pro";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { fetchNflEdgesDesk } from "@/lib/nfl-edges";
import { loadAssembledEdgeBoardRows } from "@/lib/build-edge-board-rows";
import {
  isFootballPublicNumbersDisabled,
  isNflFairLinesCustomerSurfaceClosed,
} from "@/lib/cfb-edge-board-public";
import { GET as getNflFair } from "@/app/api/nfl/fair-lines/route";
import { GET as getEdgesDesk } from "@/app/api/nfl/edges-desk/route";
import { GET as getAssemble } from "@/app/api/edge-board/[sport]/assemble/route";

const C10_UNREACHABLE = new Error("Unable to reach model service.");
const C10_TIMEOUT = new UpstreamTimeoutError(
  25_000,
  "http://model-service.local/nfl/fair-lines",
);

const req = (url: string) => new Request(url);

type JsonBody = {
  error?: string;
  timeoutMs?: number;
  lines?: unknown;
  rows?: unknown;
  count?: unknown;
  games?: unknown;
  week1Count?: unknown;
  fullCount?: unknown;
  oddsAsOf?: unknown;
};

function expectNoStore(res: Response) {
  expect(res.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  expect(res.headers.get("CDN-Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  expect(res.headers.get("Cache-Control")).not.toContain("public");
  expect(res.headers.get("Cache-Control")).not.toContain("s-maxage");
}

function expectRefusedNoInvent(body: JsonBody) {
  expect(body).not.toHaveProperty("lines");
  expect(body).not.toHaveProperty("rows");
  expect(body).not.toHaveProperty("count");
  expect(body).not.toHaveProperty("games");
  expect(body).not.toHaveProperty("week1Count");
  expect(body).not.toHaveProperty("fullCount");
  expect(body).not.toHaveProperty("oddsAsOf");
}

describe("T6-API-C10-CONSUMER-REFUSE (C10/model unreachable)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
    vi.mocked(isFootballPublicNumbersDisabled).mockReturnValue(false);
    vi.mocked(isNflFairLinesCustomerSurfaceClosed).mockReturnValue(false);
  });

  it("GET /api/nfl/fair-lines → 503, no invented slate, private no-store", async () => {
    vi.mocked(fetchNflFairLines).mockRejectedValue(C10_UNREACHABLE);

    const res = await getNflFair(req("http://localhost/api/nfl/fair-lines"));
    const body = (await res.json()) as JsonBody;

    expect(fetchNflFairLines).toHaveBeenCalled();
    expect(res.status).toBe(503);
    expect(body.error).toBe("Unable to reach model service.");
    expectRefusedNoInvent(body);
    expectNoStore(res);
  });

  it("GET /api/nfl/fair-lines timeout → 504 (not empty 200)", async () => {
    vi.mocked(fetchNflFairLines).mockRejectedValue(C10_TIMEOUT);

    const res = await getNflFair(req("http://localhost/api/nfl/fair-lines"));
    const body = (await res.json()) as JsonBody;

    expect(res.status).toBe(504);
    expect(body.error).toMatch(/timed out/i);
    expect(body.timeoutMs).toBe(25_000);
    expectRefusedNoInvent(body);
    expectNoStore(res);
  });

  it("GET /api/nfl/edges-desk → 503, no invented rows, private no-store", async () => {
    vi.mocked(fetchNflEdgesDesk).mockRejectedValue(C10_UNREACHABLE);

    const res = await getEdgesDesk(req("http://localhost/api/nfl/edges-desk"));
    const body = (await res.json()) as JsonBody;

    expect(fetchNflEdgesDesk).toHaveBeenCalled();
    expect(res.status).toBe(503);
    expect(body.error).toBe("Unable to reach model service.");
    expectRefusedNoInvent(body);
    expectNoStore(res);
  });

  it("GET /api/edge-board/nfl/assemble week1 → 503, no invented rows", async () => {
    vi.mocked(loadAssembledEdgeBoardRows).mockRejectedValue(C10_UNREACHABLE);

    const res = await getAssemble(
      req("http://localhost/api/edge-board/nfl/assemble?slate=week1"),
      { params: Promise.resolve({ sport: "nfl" }) },
    );
    const body = (await res.json()) as JsonBody;

    expect(loadAssembledEdgeBoardRows).toHaveBeenCalled();
    expect(res.status).toBe(503);
    expect(body.error).toBe("Unable to reach model service.");
    expectRefusedNoInvent(body);
    expectNoStore(res);
  });

  it("mutation oracle: page-data routes still throwOnTransportError + map 503/504", async () => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const root = process.cwd();
    const files = [
      "app/api/nfl/fair-lines/route.ts",
      "app/api/nfl/edges-desk/route.ts",
      "app/api/edge-board/[sport]/assemble/route.ts",
    ];
    for (const rel of files) {
      const src = readFileSync(join(root, rel), "utf8");
      expect(src, rel).toContain("throwOnTransportError: true");
      expect(src, rel).toContain("pageDataUpstreamErrorResponse");
    }
  });
});
