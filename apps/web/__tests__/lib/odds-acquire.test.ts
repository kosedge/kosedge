import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";
import path from "path";
import { withAuthorizedOddsJob } from "@/__tests__/helpers/authorized-odds-job";
import {
  enterAuthorizedOddsJobContext,
  TEST_ODDS_ACQUIRE_JOB_ID,
  WARM_PAGE_DATA_JOB_ID,
} from "@/lib/odds-acquire/context";
import { PaidFetchDenied } from "@/lib/odds-acquire/errors";
import { oddsAcquire } from "@/lib/odds-acquire/acquire";
import { ODDS_API_HOST } from "@/lib/odds-acquire/hosts";

const dummyKey = "dummy-odds-key-t4662u";

afterEach(() => {
  vi.restoreAllMocks();
  delete process.env.ODDS_WEB_PAID_FETCH_ALLOW;
  delete process.env.CRON_SECRET;
});

describe("U1 oddsAcquire default DENY", () => {
  it("throws PaidFetchDenied without job intent and never fetches", async () => {
    process.env.ODDS_API_KEY = dummyKey;
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    await expect(
      oddsAcquire({
        intent: "request",
        host: ODDS_API_HOST,
        path: "/v4/sports",
        caller: "u1-request",
      }),
    ).rejects.toBeInstanceOf(PaidFetchDenied);
    expect(fetchSpy).toHaveBeenCalledTimes(0);
  });

  it("denies when flag is 1 but ALS job context is missing", async () => {
    process.env.ODDS_WEB_PAID_FETCH_ALLOW = "1";
    process.env.CRON_SECRET = "secret";
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    await expect(
      oddsAcquire({
        intent: "job",
        jobId: TEST_ODDS_ACQUIRE_JOB_ID,
        host: ODDS_API_HOST,
        path: "/v4/sports",
        caller: "u2-no-als",
      }),
    ).rejects.toBeInstanceOf(PaidFetchDenied);
    expect(fetchSpy).toHaveBeenCalledTimes(0);
  });
});

describe("U2 authorized job allow-path (mocked host only)", () => {
  it("fetches once to the allowlisted host when flag + job context are set", async () => {
    const fetchSpy = vi.fn(async (input: RequestInfo | URL) => {
      expect(String(input)).toContain(ODDS_API_HOST);
      return new Response("[]", { status: 200 });
    });
    vi.stubGlobal("fetch", fetchSpy);
    await withAuthorizedOddsJob(() =>
      oddsAcquire({
        intent: "job",
        jobId: TEST_ODDS_ACQUIRE_JOB_ID,
        host: ODDS_API_HOST,
        path: "/v4/sports/basketball_nba/odds",
        caller: "u2-allow",
      }),
    );
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("refuses to enter ALS for warm-page-data even with a valid secret", () => {
    process.env.CRON_SECRET = "secret";
    expect(() =>
      enterAuthorizedOddsJobContext({
        jobId: WARM_PAGE_DATA_JOB_ID,
        authorization: "Bearer secret",
        fn: () => null,
      }),
    ).toThrow(PaidFetchDenied);
  });
});

describe("U3 static choke (S1–S8 host isolation)", () => {
  it("keeps the paid host only under lib/odds-acquire", () => {
    const root = path.resolve(process.cwd(), "../..");
    const out = execSync(
      "git grep -n -I -e 'the-odds-api\\.com' -- 'apps/web' ':!apps/web/lib/odds-acquire/' ':!apps/web/scripts/' ':!*.md' ':!apps/web/.env.example' ':!apps/web/__tests__/' || true",
      { cwd: root, encoding: "utf8" },
    );
    expect(out.trim()).toBe("");
    const hosts = readFileSync(
      path.join(process.cwd(), "lib/odds-acquire/hosts.ts"),
      "utf8",
    );
    expect(hosts).toContain("the-odds-api.com");
  });
});
