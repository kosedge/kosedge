import { NextResponse } from "next/server";
import { getSport } from "@/lib/sports";
import {
  bookDisplay,
  bookFeedStatusForSport,
  configuredBooksForSport,
  SPORT_KEY_MAP,
  type OddsCompareBoardPayload,
} from "@/lib/odds-api";
import { getCache } from "@/lib/cache/redis";

export const dynamic = "force-dynamic";

const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = {
  "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600",
};

type ComparePayload = OddsCompareBoardPayload;

const compareCache = new Map<string, { data: ComparePayload; ts: number }>();
/** v8: designated books carry feedStatus (not_carried vs empty line). */
const compareCacheKeyForSport = (sport: string) => `odds:${sport}:compare:v8`;

function booksForSport(sport: string): ComparePayload["books"] {
  return configuredBooksForSport(sport).map((k) => ({
    key: k,
    label: bookDisplay(k),
    feedStatus: bookFeedStatusForSport(sport, k),
  }));
}

function emptyPayload(
  sport: string,
  extras: Pick<ComparePayload, "source" | "reason" | "availability">,
): ComparePayload {
  return {
    rows: [],
    books: booksForSport(sport),
    asOf: null,
    bookAsOf: [],
    ...extras,
  };
}

function withReadMeta(
  data: ComparePayload,
  extras: Pick<ComparePayload, "source" | "reason" | "availability">,
): ComparePayload {
  return { ...data, ...extras };
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

  if (!SPORT_KEY_MAP[sport]) {
    return NextResponse.json(
      emptyPayload(sport, {
        source: "none",
        reason: "paid_fetch_denied",
        availability: "unavailable",
      }),
      { headers: CACHE_HEADERS },
    );
  }

  const now = Date.now();
  const cached = compareCache.get(sport);
  if (cached && cached.data.rows.length > 0) {
    const stale = now - cached.ts >= ODDS_CACHE_TTL_MS;
    return NextResponse.json(
      withReadMeta(cached.data, {
        source: "cache",
        reason: stale ? "stale" : "ok",
        availability: stale ? "stale" : "ok",
      }),
      { headers: CACHE_HEADERS },
    );
  }

  const distributed = await getCache<{
    data: ComparePayload;
    ts: number;
  }>(compareCacheKeyForSport(sport));
  if (distributed && distributed.data.rows.length > 0) {
    compareCache.set(sport, distributed);
    const stale = now - distributed.ts >= ODDS_CACHE_TTL_MS;
    return NextResponse.json(
      withReadMeta(distributed.data, {
        source: "snapshot",
        reason: stale ? "stale" : "ok",
        availability: stale ? "stale" : "ok",
      }),
      { headers: CACHE_HEADERS },
    );
  }

  // Cache miss / Redis absent: FAIL CLOSED. Never live-pull.
  return NextResponse.json(
    emptyPayload(sport, {
      source: "none",
      reason: "paid_fetch_denied",
      availability: "unavailable",
    }),
    { headers: CACHE_HEADERS },
  );
}
