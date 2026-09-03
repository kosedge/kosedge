import { NextResponse } from "next/server";

/**
 * Short CDN/browser cache for NFL page-data JSON (KEI Lines / edges / assemble).
 * 45s sits in the 30–60s band — enough to absorb subscriber stampedes without
 * minting a request clock (oddsAsOf / linesAsOf stay book vintage).
 */
export const PAGE_DATA_CACHE_S_MAXAGE = 45;
export const PAGE_DATA_CACHE_SWR = 45;

export const PAGE_DATA_CACHE_CONTROL = `public, s-maxage=${PAGE_DATA_CACHE_S_MAXAGE}, stale-while-revalidate=${PAGE_DATA_CACHE_SWR}`;
export const PAGE_DATA_NO_STORE = "private, no-store";

export type PageDataCacheDecision = {
  /** True only for HTTP 200 with a non-empty board (count/games > 0). */
  cacheable: boolean;
};

/**
 * Never cache 503/504, auth failures, transport errors, or empty count=0 boards.
 * Cached bodies must already carry oddsAsOf / linesAsOf from upstream — never Date.now().
 */
export function pageDataCacheHeaders(
  decision: PageDataCacheDecision,
): Record<string, string> {
  return {
    "Cache-Control": decision.cacheable
      ? PAGE_DATA_CACHE_CONTROL
      : PAGE_DATA_NO_STORE,
  };
}

export function isPageDataCountCacheable(
  status: number,
  count: number | null | undefined,
): boolean {
  return status === 200 && typeof count === "number" && count > 0;
}

/** JSON response with page-data Cache-Control (cacheable only when count > 0). */
export function pageDataJsonResponse<
  T extends { count?: number; games?: number },
>(body: T, init?: { status?: number }): NextResponse {
  const status = init?.status ?? 200;
  const count =
    typeof body.count === "number"
      ? body.count
      : typeof body.games === "number"
        ? body.games
        : 0;
  return NextResponse.json(body, {
    status,
    headers: pageDataCacheHeaders({
      cacheable: isPageDataCountCacheable(status, count),
    }),
  });
}
