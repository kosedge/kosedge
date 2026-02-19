import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { getSport } from "@/lib/sports";
import { fetchEdgeBoard, SPORT_KEY_MAP } from "@/lib/odds-api";

export const dynamic = "force-dynamic";

/** Odds refresh at most every 6 hours */
const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = {
  "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600",
};

const sportCache = new Map<string, { rows: unknown[]; ts: number }>();

function json(data: unknown, status = 200, extraHeaders?: Record<string, string>) {
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
  { params }: { params: Promise<{ sport: string }> }
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
      return json({ error: "Unauthorized", requestId }, 401, { "x-request-id": requestId });
    }
  }

  const key = env.ODDS_API_KEY?.trim();
  if (!key || !SPORT_KEY_MAP[sport]) {
    return json({ rows: [] }, 200, { "x-request-id": requestId });
  }

  const now = Date.now();
  const cached = sportCache.get(sport);
  if (cached && now - cached.ts < ODDS_CACHE_TTL_MS) {
    return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
  }

  try {
    const rows = await fetchEdgeBoard(sport, key);
    const parsed = EdgeBoardResponseSchema.safeParse({ rows });
    if (!parsed.success) {
      if (cached) return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
      return json({ rows: [] }, 200, { "x-request-id": requestId });
    }
    sportCache.set(sport, { rows: parsed.data.rows, ts: now });
    return json(parsed.data, 200, { "x-request-id": requestId });
  } catch (e) {
    console.error("edge_board_odds_failed", { sport, error: String(e) });
    if (cached) return json({ rows: cached.rows }, 200, { "x-request-id": requestId });
    return json({ rows: [] }, 200, { "x-request-id": requestId });
  }
}
