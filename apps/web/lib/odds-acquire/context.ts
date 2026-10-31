import { timingSafeEqual } from "node:crypto";
import { AsyncLocalStorage } from "node:async_hooks";
import { PaidFetchDenied } from "@/lib/odds-acquire/errors";

/**
 * Web paid-Odds jobs. Empty on purpose: beat/worker is the sole sanctioned
 * acquirer (model-service). A future web job needs a separate CLEAR + budget.
 * `test-odds-acquire` is NODE_ENV=test only (U2 allow-path).
 */
export const REGISTERED_ODDS_ACQUIRE_JOB_IDS = new Set<string>([]);

export const TEST_ODDS_ACQUIRE_JOB_ID = "test-odds-acquire";

/** Warm primes SoT-backed responses. It is never an acquisition job. */
export const WARM_PAGE_DATA_JOB_ID = "warm-page-data";

export type OddsJobIntent = "job";

export type OddsJobContext = {
  intent: OddsJobIntent;
  jobId: string;
  cronVerified: true;
};

const als = new AsyncLocalStorage<OddsJobContext>();

function encodeUtf8(value: string): Uint8Array {
  return new TextEncoder().encode(value);
}

/** Constant-time string compare. Length mismatch still hashes both sides. */
export function timingSafeEqualString(left: string, right: string): boolean {
  const a = encodeUtf8(left);
  const b = encodeUtf8(right);
  const max = Math.max(a.length, b.length, 1);
  const ax = new Uint8Array(max);
  const bx = new Uint8Array(max);
  ax.set(a);
  bx.set(b);
  const sameLen = a.length === b.length;
  return timingSafeEqual(ax, bx) && sameLen;
}

export function verifyCronBearer(
  authorization: string | null | undefined,
): boolean {
  const secret = process.env.CRON_SECRET?.trim();
  if (!secret) return false;
  const got = String(authorization ?? "");
  return timingSafeEqualString(got, `Bearer ${secret}`);
}

export function isRegisteredOddsAcquireJob(jobId: string): boolean {
  if (REGISTERED_ODDS_ACQUIRE_JOB_IDS.has(jobId)) return true;
  return process.env.NODE_ENV === "test" && jobId === TEST_ODDS_ACQUIRE_JOB_ID;
}

export function getOddsJobContext(): OddsJobContext | undefined {
  return als.getStore();
}

export function webPaidFetchAllowEnabled(): boolean {
  return process.env.ODDS_WEB_PAID_FETCH_ALLOW === "1";
}

/**
 * Establish authorized job ALS after constant-time CRON_SECRET verify.
 * Headers (x-kosedge-warm / x-vercel-cron / UA / query) never enter here.
 */
export function enterAuthorizedOddsJobContext<T>(args: {
  jobId: string;
  authorization: string | null | undefined;
  fn: () => T;
}): T {
  if (args.jobId === WARM_PAGE_DATA_JOB_ID) {
    throw new PaidFetchDenied(args.jobId, "warm_is_not_an_acquisition_job");
  }
  if (!verifyCronBearer(args.authorization)) {
    throw new PaidFetchDenied(args.jobId, "cron_unverified");
  }
  if (!isRegisteredOddsAcquireJob(args.jobId)) {
    throw new PaidFetchDenied(args.jobId, "unregistered_job");
  }
  return als.run(
    { intent: "job", jobId: args.jobId, cronVerified: true },
    args.fn,
  );
}

export function isAuthorizedOddsAcquireContext(): boolean {
  const ctx = als.getStore();
  if (!webPaidFetchAllowEnabled()) return false;
  if (!ctx) return false;
  if (ctx.intent !== "job") return false;
  if (ctx.cronVerified !== true) return false;
  if (ctx.jobId === WARM_PAGE_DATA_JOB_ID) return false;
  return isRegisteredOddsAcquireJob(ctx.jobId);
}
