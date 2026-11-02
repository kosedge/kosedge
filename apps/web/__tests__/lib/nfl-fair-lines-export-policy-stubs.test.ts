/**
 * t5178u export-policy stubs that do not depend on M0 types.
 * NFL∉HONESTY · 503 ≠ empty-success · closed customer gates stay closed.
 * CERT=0. No live fetch. No access flip.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  FAIR_LINES_HONEST_EMPTY_STATUSES,
  FAIR_LINES_HONESTY_SPORTS,
} from "@/lib/fair-lines-api-board";
import {
  NFL_EDGE_BOARD_UNAVAILABLE_CODE,
  isNflFairLinesCustomerSurfaceClosed,
  nflEdgeBoardAssembleUnavailablePayload,
} from "@/lib/cfb-edge-board-public";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(),
}));

vi.mock("@/lib/nfl-fair-lines", () => ({
  fetchNflFairLines: vi.fn(),
}));

import { getProAccessState } from "@/lib/auth/pro";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { GET as getNflFair } from "@/app/api/nfl/fair-lines/route";

const webRoot = path.join(__dirname, "../..");

function readWeb(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

describe("t5178u NFL∉HONESTY + 503≠empty-success (no M0 types)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
  });

  it("excludes NFL from FAIR_LINES_HONESTY_SPORTS", () => {
    expect(FAIR_LINES_HONESTY_SPORTS).toEqual([
      "cfb",
      "mlb",
      "nba",
      "nhl",
      "wnba",
      "ncaaf",
    ]);
    expect(FAIR_LINES_HONESTY_SPORTS).not.toContain("nfl");
    expect(FAIR_LINES_HONEST_EMPTY_STATUSES.has("no_slate")).toBe(true);
  });

  it("NFL fair-lines route does not import the common-sports honesty helper", () => {
    const api = readWeb("app/api/nfl/fair-lines/route.ts");
    expect(api).not.toContain("fair-lines-api-board");
    expect(api).not.toContain("honestEmptyFairLinesBoard");
    expect(api).not.toContain("FAIR_LINES_HONESTY_SPORTS");
    expect(api).not.toContain("FAIR_LINES_HONEST_EMPTY");
    expect(api).toContain("isNflFairLinesCustomerSurfaceClosed");
    expect(api).toContain("nflEdgeBoardAssembleUnavailablePayload");
    expect(api).toContain("persistOdds: false");
    expect(api).toContain("status: 503");
  });

  it("closed customer surface stays closed", () => {
    expect(isNflFairLinesCustomerSurfaceClosed()).toBe(true);
  });

  it("authorized closed GET is 503 unavailable, not 200 empty-success", async () => {
    expect(isNflFairLinesCustomerSurfaceClosed()).toBe(true);
    const res = await getNflFair(
      new Request("http://localhost/api/nfl/fair-lines"),
    );
    const body = (await res.json()) as Record<string, unknown>;
    const expected = nflEdgeBoardAssembleUnavailablePayload();

    expect(res.status).toBe(503);
    expect(res.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);
    expect(res.headers.get("CDN-Cache-Control")).toBe(PAGE_DATA_NO_STORE);
    expect(body).toEqual(expected);
    expect(body.error).toBe(NFL_EDGE_BOARD_UNAVAILABLE_CODE);
    expect(body.games).toBe(0);
    expect(body.rows).toEqual([]);
    expect(body.linesAsOf).toBeNull();
    expect(body).not.toHaveProperty("slateStatus");
    expect(body).not.toHaveProperty("lines");
    expect(fetchNflFairLines).not.toHaveBeenCalled();
  });

  it("503 payload is not an honest-empty success board", () => {
    const payload = nflEdgeBoardAssembleUnavailablePayload();
    expect(payload.error).toBe(NFL_EDGE_BOARD_UNAVAILABLE_CODE);
    expect(payload.games).toBe(0);
    expect(payload.rows).toEqual([]);
    const asRecord = payload as Record<string, unknown>;
    expect(asRecord.slateStatus).toBeUndefined();
    expect(
      FAIR_LINES_HONEST_EMPTY_STATUSES.has(String(asRecord.slateStatus ?? "")),
    ).toBe(false);
  });

  it("UI treats non-OK fair-lines as error, not ready empty slate", () => {
    const client = readWeb("components/pro/nfl/NflFairLinesClient.tsx");
    expect(client).toContain('if (!res.ok) throw new Error(`fair-lines ${res.status}`)');
    expect(client).toContain('error: "Unable to reach KEI Lines."');
    expect(client).not.toContain("honestEmptyFairLinesBoard");
    expect(client).not.toContain("FAIR_LINES_HONESTY_SPORTS");

    const page = readWeb("app/(pro)/pro/nfl/fair-lines/page.tsx");
    expect(page).toContain("isNflFairLinesCustomerSurfaceClosed");
    expect(page).toContain("FootballNumbersUnavailable");
    expect(page).toContain("Coming soon");
    expect(page).not.toContain("fair-lines-api-board");
  });

  it("export script keeps a versioned NFL status contract and does not copy HONESTY", () => {
    const exportSrc = readFileSync(
      path.join(webRoot, "scripts/export_kei_lines_nfl.py"),
      "utf8",
    );
    expect(exportSrc).toContain("nfl-export-status-v1");
    expect(exportSrc).toContain("actionable");
    expect(exportSrc).not.toContain("FAIR_LINES_HONESTY_SPORTS");
    expect(exportSrc).not.toContain("FAIR_LINES_HONEST_EMPTY");
    expect(exportSrc).toContain("unexpected_empty_payload");
    expect(exportSrc).toContain("blank_required_identity");
    expect(exportSrc).toContain("malformed_numeric");
    expect(exportSrc).toContain("os.replace");
  });
});
