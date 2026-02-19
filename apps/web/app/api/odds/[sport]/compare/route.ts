import { NextResponse } from "next/server";
import { env } from "@/lib/config/env";
import { getSport } from "@/lib/sports";
import { fetchOddsComparison, ALLOWED_BOOKS, bookDisplay, SPORT_KEY_MAP } from "@/lib/odds-api";

export const dynamic = "force-dynamic";

const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = { "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600" };
const compareCache = new Map<string, { data: { rows: unknown[]; books: unknown[] }; ts: number }>();

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sport: string }> }
) {
  const { sport } = await params;
  const valid = getSport(sport);
  if (!valid) {
    return NextResponse.json({ error: "Unknown sport", sport }, { status: 400 });
  }

  const key = env.ODDS_API_KEY?.trim();
  if (!key || !SPORT_KEY_MAP[sport]) {
    return NextResponse.json({ rows: [], books: [] }, { headers: CACHE_HEADERS });
  }

  const now = Date.now();
  const cached = compareCache.get(sport);
  if (cached && now - cached.ts < ODDS_CACHE_TTL_MS) {
    return NextResponse.json(cached.data, { headers: CACHE_HEADERS });
  }

  try {
    const rows = await fetchOddsComparison(sport, key);
    const books = ALLOWED_BOOKS.map((k) => ({ key: k, label: bookDisplay(k) }));
    const data = { rows, books };
    compareCache.set(sport, { data, ts: now });
    return NextResponse.json(data, { headers: CACHE_HEADERS });
  } catch (e) {
    console.error("odds_compare_failed", { sport, error: String(e) });
    if (cached) return NextResponse.json(cached.data, { headers: CACHE_HEADERS });
    return NextResponse.json({ rows: [], books: [] }, { headers: CACHE_HEADERS });
  }
}
