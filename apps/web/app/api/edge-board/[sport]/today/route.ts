import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";
import { logError } from "@/lib/logger";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { assembleEdgeBoardRows } from "@/lib/build-edge-board-rows";
import { loadEdgeBoardFallback } from "@/lib/edge-board-fallback";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { getSport } from "@/lib/sports";
import { fetchEdgeBoard, SPORT_KEY_MAP } from "@/lib/odds-api";
import { getCache, setCache } from "@/lib/cache/redis";

export const dynamic = "force-dynamic";

/** Odds refresh at most every 6 hours to avoid burning API credits (500/mo free tier). */
const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = {
  "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600",
};

const sportCache = new Map<string, { rows: unknown[]; ts: number }>();
/** v7: live=current week; all=odds-posted games; odds persisted via fair-lines. */
const cacheKeyForSport = (sport: string, slate: string) =>
  `edge-board:${sport}:today:v7:${slate}`;

function json(
  data: unknown,
  status = 200,
  extraHeaders?: Record<string, string>,
) {
  return NextResponse.json(data, {
    status,
    headers: {
      ...CACHE_HEADERS,
      ...extraHeaders,
    },
  });
}

function getRequestId(req: Request) {
  return (
    req.headers.get("x-request-id") ||
    req.headers.get("x-correlation-id") ||
    crypto.randomUUID()
  );
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ sport: string }> },
) {
  const { sport } = await params;
  const valid = getSport(sport);
  if (!valid) {
    return json({ error: "Unknown sport", sport }, 400);
  }

  const requestId = getRequestId(req);

  const expected = env.INTERNAL_API_SECRET;
  if (expected) {
    const provided = req.headers.get("x-kosedge-secret");
    if (provided !== expected) {
      return json({ error: "Unauthorized", requestId }, 401, {
        "x-request-id": requestId,
      });
    }
  }

  const now = Date.now();
  const url = new URL(req.url);
  const skipCache = url.searchParams.get("refresh") === "1";
  const slateParam = url.searchParams.get("slate");
  // NFL: week1 (default) | full. Legacy aliases: live → week1, all → full.
  const slateRaw = String(slateParam ?? "")
    .trim()
    .toLowerCase();
  const slate: "week1" | "full" =
    sport === "nfl" && (slateRaw === "full" || slateRaw === "all")
      ? "full"
      : "week1";
  const cacheBucket = `${sport}:${slate}`;
  const cached = sportCache.get(cacheBucket);
  if (!skipCache && cached && now - cached.ts < ODDS_CACHE_TTL_MS) {
    return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
  }
  if (!skipCache) {
    const distributed = await getCache<{ rows: unknown[]; ts: number }>(
      cacheKeyForSport(sport, slate),
    );
    if (distributed && now - distributed.ts < ODDS_CACHE_TTL_MS) {
      sportCache.set(cacheBucket, distributed);
      return json({ rows: distributed.rows }, 200, {
        "x-request-id": requestId,
      });
    }
  }

  let oddsRows: Awaited<ReturnType<typeof fetchEdgeBoard>> = [];
  const keys = getOddsApiKeys();
  if (keys.length && SPORT_KEY_MAP[sport]) {
    for (const key of keys) {
      try {
        oddsRows = await fetchEdgeBoard(sport, key);
        if (oddsRows.length > 0) break;
      } catch (e) {
        logError(e instanceof Error ? e : new Error(String(e)), {
          sport,
          route: "edge-board/today",
        });
      }
    }
  }

  if (
    oddsRows.length === 0 &&
    cached &&
    (cached.rows as unknown[]).length > 0
  ) {
    return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
  }

  // When Odds API is empty (quota/outage), use shipped last-known snapshot.
  if (oddsRows.length === 0) {
    oddsRows = loadEdgeBoardFallback(sport);
  }

  try {
    const rows = await assembleEdgeBoardRows(sport, oddsRows, { slate });
    const parsed = EdgeBoardResponseSchema.safeParse({ rows });
    if (!parsed.success) {
      if (cached)
        return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
      return json({ rows: [] }, 200, { "x-request-id": requestId });
    }
    sportCache.set(cacheBucket, { rows: parsed.data.rows, ts: now });
    await setCache(
      cacheKeyForSport(sport, slate),
      { rows: parsed.data.rows, ts: now },
      Math.ceil(ODDS_CACHE_TTL_MS / 1000),
    );
    return json(parsed.data, 200, { "x-request-id": requestId });
  } catch (e) {
    logError(e instanceof Error ? e : new Error(String(e)), {
      sport,
      route: "edge-board/today",
    });
    if (cached)
      return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
    return json({ rows: [] }, 200, { "x-request-id": requestId });
  }
}
