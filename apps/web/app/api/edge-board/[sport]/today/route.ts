import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";
import { logError } from "@/lib/logger";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { mergeKeiIntoEdgeBoardRows } from "@/lib/edge-board-kei";
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
const cacheKeyForSport = (sport: string) => `edge-board:${sport}:today:v2`;

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

  const keys = getOddsApiKeys();
  if (!keys.length || !SPORT_KEY_MAP[sport]) {
    return json({ rows: [] }, 200, { "x-request-id": requestId });
  }

  const now = Date.now();
  const url = new URL(req.url);
  const skipCache = url.searchParams.get("refresh") === "1";
  const cached = sportCache.get(sport);
  if (!skipCache && cached && now - cached.ts < ODDS_CACHE_TTL_MS) {
    return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
  }
  if (!skipCache) {
    const distributed = await getCache<{ rows: unknown[]; ts: number }>(
      cacheKeyForSport(sport),
    );
    if (distributed && now - distributed.ts < ODDS_CACHE_TTL_MS) {
      sportCache.set(sport, distributed);
      return json({ rows: distributed.rows }, 200, { "x-request-id": requestId });
    }
  }

  let rows: Awaited<ReturnType<typeof fetchEdgeBoard>> = [];
  for (const key of keys) {
    try {
      rows = await fetchEdgeBoard(sport, key);
      if (rows.length > 0) break;
    } catch (e) {
      logError(e instanceof Error ? e : new Error(String(e)), {
        sport,
        route: "edge-board/today",
      });
    }
  }
  if (rows.length === 0 && cached) {
    return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
  }
  try {
    rows = mergeKeiIntoEdgeBoardRows(rows, sport);
    const parsed = EdgeBoardResponseSchema.safeParse({ rows });
    if (!parsed.success) {
      if (cached)
        return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
      return json({ rows: [] }, 200, { "x-request-id": requestId });
    }
    sportCache.set(sport, { rows: parsed.data.rows, ts: now });
    await setCache(cacheKeyForSport(sport), { rows: parsed.data.rows, ts: now }, Math.ceil(ODDS_CACHE_TTL_MS / 1000));
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
