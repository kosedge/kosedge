import "server-only";

export {
  ODDS_API_HOST,
  ODDS_API_ORIGIN,
  ODDS_PAID_HOSTS,
  ODDS_WIDGET_HOST,
  ODDS_WIDGET_ORIGIN,
  isOddsPaidHost,
  isOddsPaidUrl,
} from "@/lib/odds-acquire/hosts";
export { PaidFetchDenied, isPaidFetchDenied } from "@/lib/odds-acquire/errors";
export {
  REGISTERED_ODDS_ACQUIRE_JOB_IDS,
  TEST_ODDS_ACQUIRE_JOB_ID,
  WARM_PAGE_DATA_JOB_ID,
  enterAuthorizedOddsJobContext,
  getOddsJobContext,
  isAuthorizedOddsAcquireContext,
  isRegisteredOddsAcquireJob,
  timingSafeEqualString,
  verifyCronBearer,
  webPaidFetchAllowEnabled,
} from "@/lib/odds-acquire/context";
export { oddsAcquire } from "@/lib/odds-acquire/acquire";
export type {
  OddsAcquireArgs,
  OddsAcquireIntent,
} from "@/lib/odds-acquire/acquire";
export {
  fetchEdgeBoard,
  fetchNcaabEdgeBoard,
  fetchOddsComparison,
} from "@/lib/odds-acquire/odds-fetch";
