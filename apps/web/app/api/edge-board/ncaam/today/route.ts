import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";

export const dynamic = "force-dynamic";

const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = {
  "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600",
};

let ncaamCache: { rows: unknown[]; ts: number } | null = null;

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

export async function GET(req: Request) {
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
  if (ncaamCache) {
    const stale = now - ncaamCache.ts >= ODDS_CACHE_TTL_MS;
    return json(
      {
        rows: ncaamCache.rows,
        source: "cache",
        reason: stale ? "stale" : "ok",
        availability: stale ? "stale" : "ok",
      },
      200,
      { "x-request-id": requestId },
    );
  }

  // G-NCAAM-PROXY: user-read never proxies Railway /edge-board/ncaam/today
  // (that route live-fetched NCAAB Odds). Cache is the only SoT read.
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
