import { NextResponse } from "next/server";
import { logError } from "@/lib/logger";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { getSport } from "@/lib/sports";
import {
  fetchOddsComparison,
  bookDisplay,
  configuredBooksForSport,
  SPORT_KEY_MAP,
  type OddsComparisonBookAsOf,
  type OddsComparisonRow,
} from "@/lib/odds-api";
import { getCache, setCache } from "@/lib/cache/redis";

export const dynamic = "force-dynamic";

const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = {
  "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600",
};

type ComparePayload = {
  rows: OddsComparisonRow[];
  books: { key: string; label: string }[];
  /** Max book/market last_update; null when upstream omitted stamps. */
  asOf: string | null;
  bookAsOf: OddsComparisonBookAsOf[];
};

const compareCache = new Map<string, { data: ComparePayload; ts: number }>();
/** v6: include honest market asOf / bookAsOf (no fabricated fetch clock). */
const compareCacheKeyForSport = (sport: string) => `odds:${sport}:compare:v6`;

function emptyPayload(sport: string): ComparePayload {
  return {
    rows: [],
    books: configuredBooksForSport(sport).map((k) => ({
      key: k,
      label: bookDisplay(k),
    })),
    asOf: null,
    bookAsOf: [],
  };
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sport: string }> },
) {
  const { sport } = await params;
  const valid = getSport(sport);
  if (!valid) {
    return NextResponse.json(
      { error: "Unknown sport", sport },
      { status: 400 },
    );
  }

  const keys = getOddsApiKeys();
  if (!keys.length || !SPORT_KEY_MAP[sport]) {
    return NextResponse.json(emptyPayload(sport), { headers: CACHE_HEADERS });
  }

  const now = Date.now();
  const cached = compareCache.get(sport);
  if (
    cached &&
    cached.data.rows.length > 0 &&
    now - cached.ts < ODDS_CACHE_TTL_MS
  ) {
    return NextResponse.json(cached.data, { headers: CACHE_HEADERS });
  }
  const distributed = await getCache<{
    data: ComparePayload;
    ts: number;
  }>(compareCacheKeyForSport(sport));
  if (
    distributed &&
    distributed.data.rows.length > 0 &&
    now - distributed.ts < ODDS_CACHE_TTL_MS
  ) {
    compareCache.set(sport, distributed);
    return NextResponse.json(distributed.data, { headers: CACHE_HEADERS });
  }

  let comparison: Awaited<ReturnType<typeof fetchOddsComparison>> = {
    rows: [],
    asOf: null,
    bookAsOf: [],
  };
  let fetchErrors = 0;
  for (const key of keys) {
    try {
      comparison = await fetchOddsComparison(sport, key);
      if (comparison.rows.length > 0) break;
    } catch (e) {
      fetchErrors += 1;
      logError(e instanceof Error ? e : new Error(String(e)), {
        sport,
        route: "odds/compare",
      });
    }
  }
  if (comparison.rows.length === 0 && cached && cached.data.rows.length > 0) {
    return NextResponse.json(cached.data, { headers: CACHE_HEADERS });
  }
  try {
    const books = configuredBooksForSport(sport).map((k) => ({
      key: k,
      label: bookDisplay(k),
    }));
    const data: ComparePayload = {
      rows: comparison.rows,
      books,
      asOf: comparison.asOf,
      bookAsOf: comparison.bookAsOf,
    };
    const payload = { data, ts: now };
    // Never persist empty payloads after API failures — that froze Compare Odds
    // for the full 6h TTL when the primary key was out of credits.
    if (comparison.rows.length > 0 || fetchErrors === 0) {
      compareCache.set(sport, payload);
      await setCache(
        compareCacheKeyForSport(sport),
        payload,
        Math.ceil(ODDS_CACHE_TTL_MS / 1000),
      );
    }
    return NextResponse.json(data, { headers: CACHE_HEADERS });
  } catch (e) {
    logError(e instanceof Error ? e : new Error(String(e)), {
      sport,
      route: "odds/compare",
    });
    if (cached && cached.data.rows.length > 0)
      return NextResponse.json(cached.data, { headers: CACHE_HEADERS });
    return NextResponse.json(emptyPayload(sport), { headers: CACHE_HEADERS });
  }
}
