import "server-only";

import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import { logWarn } from "@/lib/logger";
import {
  getOddsJobContext,
  isAuthorizedOddsAcquireContext,
  webPaidFetchAllowEnabled,
} from "@/lib/odds-acquire/context";
import { PaidFetchDenied } from "@/lib/odds-acquire/errors";
import {
  isOddsPaidHost,
  ODDS_API_ORIGIN,
  ODDS_WIDGET_ORIGIN,
} from "@/lib/odds-acquire/hosts";

export type OddsAcquireIntent = "job" | "request";

export type OddsAcquireArgs = {
  /** Caller-declared intent. Request/SSR/page never qualify. */
  intent?: OddsAcquireIntent;
  jobId?: string;
  host: string;
  path: string;
  caller: string;
  init?: RequestInit & { timeoutMs?: number };
};

function deny(caller: string, extra?: Record<string, unknown>): never {
  logWarn("PAID_FETCH_DENIED", {
    caller,
    allow: webPaidFetchAllowEnabled(),
    jobId: getOddsJobContext()?.jobId ?? null,
    ...extra,
  });
  throw new PaidFetchDenied(caller);
}

/**
 * Sole paid Odds HTTP exit. Default DENY.
 * Allow only: ALS job + CRON_SECRET-verified context + flag=1 + registered jobId.
 */
export async function oddsAcquire(args: OddsAcquireArgs): Promise<Response> {
  const caller = args.caller || args.path || "unknown";
  if (args.intent && args.intent !== "job") {
    deny(caller, { intent: args.intent });
  }
  if (!isAuthorizedOddsAcquireContext()) {
    deny(caller);
  }
  const ctx = getOddsJobContext();
  if (args.jobId && ctx && args.jobId !== ctx.jobId) {
    deny(caller, { jobIdMismatch: true });
  }
  const host = String(args.host ?? "")
    .trim()
    .toLowerCase();
  if (!isOddsPaidHost(host)) {
    deny(caller, { host });
  }
  const origin = host.startsWith("widget.")
    ? ODDS_WIDGET_ORIGIN
    : ODDS_API_ORIGIN;
  const path = args.path.startsWith("/") ? args.path : `/${args.path}`;
  const url = `${origin}${path}`;
  return upstreamFetch(url, {
    cache: "no-store",
    timeoutMs: args.init?.timeoutMs ?? UPSTREAM_TIMEOUT_MS.fast,
    ...args.init,
  });
}
