/**
 * t5178u W-FIX-B — same M0 contract wired into actual NFL consumers.
 * CERT=0. Synthetic only. No simulator / network / DB / jobs.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  FAIR_LINES_HONESTY_SPORTS,
} from "@/lib/fair-lines-api-board";
import {
  FIXTURE_CONTRACT_ID,
  FIXTURE_ELIGIBILITY_RESULTS,
  FixtureHardRefuse,
  allowFixtureEligibility,
  consumeFixtureEligibility,
  type EligibilityDecisionInput,
  type FixtureEligibilityResult,
  type SyntheticQuote,
} from "@/lib/nfl-fixture-assembly-contract";
import { projectFixtureFairLinesBoard } from "@/lib/nfl-fair-lines";
import {
  assertCustomerFairLinesViewModel,
  projectFixtureFairLinesViewModel,
} from "@/lib/nfl-fair-lines-view-types";
import {
  keiGamesFromFixtureFairLines,
} from "@/lib/resolve-kei-lines";
import {
  PAGE_DATA_NO_STORE,
  invalidateFixtureProjectionCache,
  pageDataCacheHeadersForFixture,
  readFixtureProjectionCache,
  writeFixtureProjectionCache,
} from "@/lib/page-data-cache";

vi.mock("@/lib/auth/pro", () => ({
  getProAccessState: vi.fn(),
}));
vi.mock("@/lib/nfl-fair-lines", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/nfl-fair-lines")>();
  return {
    ...actual,
    fetchNflFairLines: vi.fn(),
  };
});

import { getProAccessState } from "@/lib/auth/pro";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { GET as getNflFair } from "@/app/api/nfl/fair-lines/route";
import {
  nflFairLinesCustomerUnavailableResponse,
  projectFixtureFairLinesApiResponse,
} from "@/lib/nfl-fair-lines-fixture-api";

const webRoot = path.join(__dirname, "../..");
const repoRoot = path.join(webRoot, "../..");

function readWeb(rel: string): string {
  return readFileSync(path.join(webRoot, rel), "utf8");
}

function readRepo(rel: string): string {
  return readFileSync(path.join(repoRoot, rel), "utf8");
}

function quote(overrides: Partial<SyntheticQuote> = {}): SyntheticQuote {
  return {
    book: "synth-book",
    event_id: "2026_10_AAA_BBB",
    side: "HOME",
    period: "full_game",
    line: -3,
    price: -110,
    time: "2026-11-08T16:00:00Z",
    fixture: true,
    transport_only: true,
    injury_policy_approved: false,
    ...overrides,
  };
}

function allow() {
  return allowFixtureEligibility();
}

describe("t5178u W-FIX-B same-contract consumer wiring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProAccessState).mockResolvedValue("authorized");
    invalidateFixtureProjectionCache("wfixb");
  });

  it("uses the SAME contract id as Python SoT (not a demo helper)", () => {
    const py = readRepo(
      "services/model-service/src/services/nfl_fixture_assembly/contract.py",
    );
    const ts = readWeb("lib/nfl-fixture-assembly-contract.ts");
    const exportSrc = readWeb("scripts/export_kei_lines_nfl.py");
    expect(py).toContain(`CONTRACT_ID = "${FIXTURE_CONTRACT_ID}"`);
    expect(ts).toContain(`FIXTURE_CONTRACT_ID = "${FIXTURE_CONTRACT_ID}"`);
    expect(exportSrc).toContain(`FIXTURE_CONTRACT_ID = "${FIXTURE_CONTRACT_ID}"`);
    expect(FAIR_LINES_HONESTY_SPORTS).not.toContain("nfl");
  });

  it("wires contract consume into API / client / export / cache / view-model files", () => {
    expect(readWeb("lib/nfl-fair-lines-fixture-api.ts")).toContain(
      "projectFixtureFairLinesApiResponse",
    );
    expect(readWeb("app/api/nfl/fair-lines/route.ts")).not.toContain(
      "projectFixtureFairLinesApiResponse",
    );
    expect(readWeb("app/api/nfl/fair-lines/route.ts")).toContain(
      "nflFairLinesCustomerUnavailableResponse",
    );
    expect(readWeb("app/api/nfl/fair-lines/route.ts")).toContain(
      "persistOdds: false",
    );
    expect(readWeb("lib/nfl-fair-lines.ts")).toContain(
      "projectFixtureFairLinesBoard",
    );
    expect(readWeb("components/pro/nfl/NflFairLinesClient.tsx")).toContain(
      "assertCustomerFairLinesViewModel",
    );
    expect(readWeb("scripts/export_kei_lines_nfl.py")).toContain(
      "project_fixture_assembly_to_export",
    );
    expect(readWeb("lib/page-data-cache.ts")).toContain(
      "pageDataCacheHeadersForFixture",
    );
    expect(readWeb("lib/resolve-kei-lines.ts")).toContain(
      "keiGamesFromFixtureFairLines",
    );
  });

  it("positive path: API / UI / export-shape / cache agree (spread only)", () => {
    const eligibility = allow();
    const input = {
      eligibility,
      consumer: "fixture",
      quote: quote(),
      homeTeam: "Kansas City Chiefs",
      awayTeam: "Buffalo Bills",
      homeAbbr: "KC",
      awayAbbr: "BUF",
    };
    const board = projectFixtureFairLinesBoard(input);
    const api = projectFixtureFairLinesApiResponse(input);
    const view = projectFixtureFairLinesViewModel(board);
    const kei = keiGamesFromFixtureFairLines(board);

    expect(board.fixture).toBe(true);
    expect(board.persistOdds).toBe(false);
    expect(board.eligibility.result).toBe("ALLOW_FIXTURE");
    expect(board.eligibility.subscriber_consumable).toBe(false);
    expect(board.eligibility.cacheable).toBe(false);
    expect(board.lines).toHaveLength(1);
    expect(board.lines[0].spreadHome).toBe(-3);
    expect(board.lines[0].totalMean).toBeNull();
    expect(board.lines[0].fairHomeMl).toBeNull();
    expect(board.lines[0].homeWinProb).toBeNull();
    expect(board.lines[0].marketJoined).toBe(false);

    expect(api.status).toBe(200);
    expect(api.board.lines[0].spreadHome).toBe(board.lines[0].spreadHome);
    expect(api.headers["Cache-Control"]).toBe(PAGE_DATA_NO_STORE);
    expect(api.headers["CDN-Cache-Control"]).toBe(PAGE_DATA_NO_STORE);

    expect(view.fixture).toBe(true);
    expect(view.subscriber_consumable).toBe(false);
    expect(view.lines[0].spreadHome).toBe(-3);
    expect(view.lines[0].totalMean).toBeNull();
    expect(view.lines[0].fairHomeMl).toBeNull();
    expect(view.lines[0].homeWinProb).toBeNull();

    expect(kei[0].fixture).toBe(true);
    expect(kei[0].projSpreadHome).toBe(-3);
    expect(kei[0].projTotal).toBeNull();
    expect(kei[0].projHomeMl).toBeUndefined();

    writeFixtureProjectionCache("wfixb", board, 1);
    expect(readFixtureProjectionCache("wfixb", 1).ok).toBe(true);
    expect(
      (readFixtureProjectionCache("wfixb", 1) as { body: { lines: { spreadHome: number }[] } }).body
        .lines[0].spreadHome,
    ).toBe(-3);
  });

  it("customer GET stays 503 unavailable and does not fetch or leak fixture", async () => {
    const res = await getNflFair(
      new Request("http://localhost/api/nfl/fair-lines"),
    );
    const body = (await res.json()) as Record<string, unknown>;
    expect(res.status).toBe(503);
    expect(body.error).toBe("nfl_edge_board_unavailable");
    expect(body.games).toBe(0);
    expect(body).not.toHaveProperty("fixture");
    expect(fetchNflFairLines).not.toHaveBeenCalled();
    const unavailable = nflFairLinesCustomerUnavailableResponse();
    expect(unavailable.status).toBe(503);
    expect(unavailable.headers.get("Cache-Control")).toBe(PAGE_DATA_NO_STORE);
  });

  it("ALLOW_FIXTURE cannot be consumed by subscriber / fair_lines_api / betting", () => {
    const eligibility = allow();
    const board = projectFixtureFairLinesBoard({
      eligibility,
      consumer: "fixture",
      quote: quote(),
    });
    for (const consumer of [
      "subscriber",
      "fair_lines_api",
      "betting",
      "production",
      "honesty_board",
      "props_eligibility",
    ] as const) {
      expect(() => consumeFixtureEligibility(eligibility, consumer)).toThrow(
        FixtureHardRefuse,
      );
      expect(() =>
        projectFixtureFairLinesBoard({
          eligibility,
          consumer,
          quote: quote(),
        }),
      ).toThrow(FixtureHardRefuse);
    }
    expect(() => assertCustomerFairLinesViewModel(board)).toThrow(
      FixtureHardRefuse,
    );
  });

  it("point-margin hard-refuses total / ML / probability channels (no partial)", () => {
    for (const requested of [
      "TOTAL",
      "MONEYLINE",
      "COVER_PROBABILITY",
      "ECONOMIC_ELIGIBILITY",
    ] as const) {
      try {
        projectFixtureFairLinesBoard({
          eligibility: allow(),
          consumer: "fixture",
          quote: quote(),
          requestedOutput: requested,
        });
        expect.unreachable(`expected refuse for ${requested}`);
      } catch (err) {
        expect(err).toBeInstanceOf(FixtureHardRefuse);
        const refuse = err as FixtureHardRefuse;
        expect(refuse.partial).toBe(false);
        expect(refuse.toDict().partial).toBe(false);
        expect(refuse.toDict()).not.toHaveProperty("lines");
      }
    }
  });

  it.each(
    FIXTURE_ELIGIBILITY_RESULTS.filter((r) => r !== "ALLOW_FIXTURE"),
  )("fault %s cannot project API/UI/export/cache success", (result) => {
    const eligibility: EligibilityDecisionInput = {
      result: result as FixtureEligibilityResult,
      reason: `synthetic ${result}`,
      fixture: true,
      subscriber_consumable: false,
      betting_consumable: false,
      production_consumable: false,
      env_bypass_honored: false,
      cacheable: false,
      contract_id: FIXTURE_CONTRACT_ID,
      schema_version: "nfl-fixture-assembly-v0",
      channel: "FIXTURE",
    };
    expect(() =>
      projectFixtureFairLinesBoard({
        eligibility,
        consumer: "fixture",
        quote: quote(),
      }),
    ).toThrow(FixtureHardRefuse);
    expect(() =>
      projectFixtureFairLinesViewModel({
        eligibility,
        lines: [],
        fixture: true,
      }),
    ).toThrow(FixtureHardRefuse);
    expect(() => consumeFixtureEligibility(eligibility, "fixture")).toThrow(
      FixtureHardRefuse,
    );
  });

  it("quote identity / period / line / sign / time faults refuse", () => {
    expect(() =>
      projectFixtureFairLinesBoard({
        eligibility: allow(),
        consumer: "fixture",
        quote: quote({ event_id: "" }),
      }),
    ).toThrow(/REFUSE_GAME/);
    expect(() =>
      projectFixtureFairLinesBoard({
        eligibility: allow(),
        consumer: "fixture",
        quote: quote({ period: "h1" }),
      }),
    ).toThrow(/REFUSE_PERIOD/);
    expect(() =>
      projectFixtureFairLinesBoard({
        eligibility: allow(),
        consumer: "fixture",
        quote: quote({ line: Number.NaN }),
      }),
    ).toThrow(/REFUSE_LINE/);
    expect(() =>
      projectFixtureFairLinesBoard({
        eligibility: allow(),
        consumer: "fixture",
        quote: quote({ time: "" }),
      }),
    ).toThrow(/REFUSE_TIME/);
  });

  it("invalidated fixture cache cannot return the prior board", () => {
    const board = projectFixtureFairLinesBoard({
      eligibility: allow(),
      consumer: "fixture",
      quote: quote(),
    });
    writeFixtureProjectionCache("wfixb", board, 7);
    expect(readFixtureProjectionCache("wfixb", 7).ok).toBe(true);
    invalidateFixtureProjectionCache("wfixb");
    expect(readFixtureProjectionCache("wfixb", 7)).toEqual({
      ok: false,
      result: "REFUSE_CACHE",
    });
    expect(readFixtureProjectionCache("wfixb", 8)).toEqual({
      ok: false,
      result: "REFUSE_CACHE",
    });
    expect(pageDataCacheHeadersForFixture(board.eligibility)["Cache-Control"]).toBe(
      PAGE_DATA_NO_STORE,
    );
  });
});
