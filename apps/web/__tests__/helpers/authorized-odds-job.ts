import { vi } from "vitest";
import {
  enterAuthorizedOddsJobContext,
  TEST_ODDS_ACQUIRE_JOB_ID,
} from "@/lib/odds-acquire/context";
import { isOddsPaidUrl } from "@/lib/odds-acquire/hosts";

const TEST_CRON = "test-cron-secret-t4662u";

/** Dummy key for I-series. Must be stubbed BEFORE `@/lib/config/env` parses. */
export const DUMMY_ODDS_KEY = "dummy-odds-key-t4662u";

export function stubDummyOddsKeys(): void {
  vi.stubEnv("ODDS_API_KEY", DUMMY_ODDS_KEY);
  vi.stubEnv("ODDS_API_KEY_BACKUP", DUMMY_ODDS_KEY);
  vi.stubEnv("ODDS_WIDGET_ACCESS_KEY", DUMMY_ODDS_KEY);
}

export async function withAuthorizedOddsJob<T>(
  fn: () => T | Promise<T>,
): Promise<T> {
  const prevAllow = process.env.ODDS_WEB_PAID_FETCH_ALLOW;
  const prevSecret = process.env.CRON_SECRET;
  process.env.ODDS_WEB_PAID_FETCH_ALLOW = "1";
  process.env.CRON_SECRET = TEST_CRON;
  try {
    return await enterAuthorizedOddsJobContext({
      jobId: TEST_ODDS_ACQUIRE_JOB_ID,
      authorization: `Bearer ${TEST_CRON}`,
      fn,
    });
  } finally {
    if (prevAllow == null) delete process.env.ODDS_WEB_PAID_FETCH_ALLOW;
    else process.env.ODDS_WEB_PAID_FETCH_ALLOW = prevAllow;
    if (prevSecret == null) delete process.env.CRON_SECRET;
    else process.env.CRON_SECRET = prevSecret;
  }
}

export function installOddsHostFailOnHit(): {
  hits: string[];
  restore: () => void;
} {
  const hits: string[] = [];
  const previous = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (isOddsPaidUrl(url)) {
      hits.push(url);
      throw new Error(`ODDS_HOST_FAIL_ON_HIT ${url}`);
    }
    return new Response(JSON.stringify({ ok: true, rows: [], events: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return {
    hits,
    restore: () => {
      globalThis.fetch = previous;
    },
  };
}
