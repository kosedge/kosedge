import { NextResponse } from "next/server";
import { env } from "@/lib/config/env";
import { jsonError, jsonOk } from "@/lib/api/response";
import { cacheControlHeader, ODDS_COMPARE_CACHE_TTL_MS } from "@/lib/constants";
import { logError } from "@/lib/logger";
import { getSport } from "@/lib/sports";
import { fetchOddsComparison, ALLOWED_BOOKS, bookDisplay, SPORT_KEY_MAP } from "@/lib/odds-api";

export const dynamic = "force-dynamic";

const compareCache = new Map<string, { data: { rows: unknown[]; books: unknown[] }; ts: number }>();

function withCacheHeaders(res: NextResponse) {
  res.headers.set("cache-control", cacheControlHeader());
  return res;
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sport: string }> }
) {
  const { sport } = await params;
  const valid = getSport(sport);
  if (!valid) {
    return jsonError(400, "Unknown sport");
  }

  const keys = [env.ODDS_API_KEY?.trim(), env.ODDS_API_KEY_BACKUP?.trim()].filter((k): k is string => Boolean(k));
  if (!keys.length || !SPORT_KEY_MAP[sport]) {
    return withCacheHeaders(jsonOk({ rows: [], books: [] }));
  }

  const now = Date.now();
  const cached = compareCache.get(sport);
  if (cached && now - cached.ts < ODDS_COMPARE_CACHE_TTL_MS) {
    return withCacheHeaders(jsonOk(cached.data));
  }

  let rows: Awaited<ReturnType<typeof fetchOddsComparison>> = [];
  for (const key of keys) {
    try {
      rows = await fetchOddsComparison(sport, key);
      break;
    } catch (e) {
      logError(e instanceof Error ? e : new Error(String(e)), { sport, route: "odds/compare" });
    }
  }
  if (rows.length === 0 && cached) {
    return withCacheHeaders(jsonOk(cached.data));
  }
  try {
    const books = ALLOWED_BOOKS.map((k) => ({ key: k, label: bookDisplay(k) }));
    const data = { rows, books };
    compareCache.set(sport, { data, ts: now });
    return withCacheHeaders(jsonOk(data));
  } catch (e) {
    logError(e instanceof Error ? e : new Error(String(e)), { sport, route: "odds/compare" });
    if (cached) return withCacheHeaders(jsonOk(cached.data));
    return withCacheHeaders(jsonOk({ rows: [], books: [] }));
  }
}
