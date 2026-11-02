import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";
import { logError } from "@/lib/logger";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { assembleEdgeBoardRows } from "@/lib/build-edge-board-rows";
import { loadEdgeBoardFallback } from "@/lib/edge-board-fallback";
import { getSport } from "@/lib/sports";
import { getCache } from "@/lib/cache/redis";

export const dynamic = "force-dynamic";

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
  // ?refresh= is not an acquisition signal — never live-pull.
  const slateParam = url.searchParams.get("slate");
  const slateRaw = String(slateParam ?? "")
    .trim()
    .toLowerCase();
  const slate: "week1" | "full" =
    sport === "nfl" && (slateRaw === "full" || slateRaw === "all")
      ? "full"
      : "week1";
  const cacheBucket = `${sport}:${slate}`;
  const cached = sportCache.get(cacheBucket);
  if (cached) {
    const stale = now - cached.ts >= ODDS_CACHE_TTL_MS;
    return json(
      {
        rows: cached.rows,
        source: "cache",
        reason: stale ? "stale" : "ok",
        availability: stale ? "stale" : "ok",
      },
      200,
      { "x-request-id": requestId },
    );
  }

  const distributed = await getCache<{ rows: unknown[]; ts: number }>(
    cacheKeyForSport(sport, slate),
  );
  if (distributed) {
    sportCache.set(cacheBucket, distributed);
    const stale = now - distributed.ts >= ODDS_CACHE_TTL_MS;
    return json(
      {
        rows: distributed.rows,
        source: "snapshot",
        reason: stale ? "stale" : "ok",
        availability: stale ? "stale" : "ok",
      },
      200,
      { "x-request-id": requestId },
    );
  }

  // Miss / Redis absent: shipped snapshot only. Never fetchEdgeBoard.
  const fallback = loadEdgeBoardFallback(sport);
  try {
    const rows = await assembleEdgeBoardRows(sport, fallback, { slate });
    const parsed = EdgeBoardResponseSchema.safeParse({ rows });
    if (!parsed.success) {
      return json(
        {
          rows: [],
          source: "none",
          reason: "paid_fetch_denied",
          availability: "unavailable",
        },
        200,
        { "x-request-id": requestId },
      );
    }
    return json(
      {
        ...parsed.data,
        source: fallback.length > 0 ? "snapshot" : "none",
        reason: fallback.length > 0 ? "stale" : "paid_fetch_denied",
        availability: fallback.length > 0 ? "stale" : "unavailable",
      },
      200,
      { "x-request-id": requestId },
    );
  } catch (e) {
    logError(e instanceof Error ? e : new Error(String(e)), {
      sport,
      route: "edge-board/today",
    });
    return json(
      {
        rows: [],
        source: "none",
        reason: "paid_fetch_denied",
        availability: "unavailable",
      },
      200,
      { "x-request-id": requestId },
    );
  }
}
