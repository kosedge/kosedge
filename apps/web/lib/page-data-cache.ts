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
  /** True only for HTTP 200 with a non-empty board. */
  cacheable: boolean;
};

export type PageDataBoardBody = {
  count?: number;
  games?: number;
  week1Count?: number;
  fullCount?: number;
  rows?: unknown[];
};

/**
 * Never cache 503/504, auth failures, transport errors, or true-empty boards.
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

/**
 * Non-empty signal for page-data boards.
 * Fair-lines / edges-desk use `count`; assemble uses `week1Count` / `fullCount` /
 * `rows` (and may omit `count` / `games`).
 */
export function pageDataBoardOccupancy(body: PageDataBoardBody): number {
  const candidates = [
    body.count,
    body.games,
    body.week1Count,
    body.fullCount,
    Array.isArray(body.rows) ? body.rows.length : undefined,
  ];
  let max = 0;
  for (const n of candidates) {
    if (typeof n === "number" && Number.isFinite(n) && n > max) max = n;
  }
  return max;
}

/** JSON response with page-data Cache-Control (cacheable only when board non-empty). */
export function pageDataJsonResponse<T extends PageDataBoardBody>(
  body: T,
  init?: { status?: number },
): NextResponse {
  const status = init?.status ?? 200;
  return NextResponse.json(body, {
    status,
    headers: pageDataCacheHeaders({
      cacheable: isPageDataCountCacheable(status, pageDataBoardOccupancy(body)),
    }),
  });
}
