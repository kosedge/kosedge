import { jsonError, jsonOk } from "@/lib/api/response";
import { ensureInternalSecret, getRequestId, withRequestId } from "@/lib/edge-board-common";
import { env } from "@/lib/config/env";
import { mergeKeiIntoEdgeBoardRows } from "@/lib/edge-board-kei";
import { cacheControlHeader, EDGE_BOARD_CACHE_TTL_MS } from "@/lib/constants";
import { logError } from "@/lib/logger";
import { getSport } from "@/lib/sports";
import { fetchEdgeBoard, SPORT_KEY_MAP } from "@/lib/odds-api";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const sportCache = new Map<string, { rows: unknown[]; ts: number }>();

function addHeaders(response: NextResponse, extra?: Record<string, string>) {
  response.headers.set("cache-control", cacheControlHeader());
  if (extra) Object.entries(extra).forEach(([k, v]) => response.headers.set(k, v));
  return response;
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ sport: string }> }
) {
  const { sport } = await params;
  const valid = getSport(sport);
  if (!valid) {
    return jsonError(400, "Unknown sport");
  }

  const requestId = getRequestId(req);

  const unauthorized = ensureInternalSecret(req, requestId);
  if (unauthorized) return unauthorized;

  const keys = [env.ODDS_API_KEY?.trim(), env.ODDS_API_KEY_BACKUP?.trim()].filter((k): k is string => Boolean(k));
  if (!keys.length || !SPORT_KEY_MAP[sport]) {
    return withRequestId(addHeaders(jsonOk({ rows: [] })), requestId);
  }

  const now = Date.now();
  const url = new URL(req.url);
  const skipCache = url.searchParams.get("refresh") === "1";
  const cached = sportCache.get(sport);
  if (!skipCache && cached && now - cached.ts < EDGE_BOARD_CACHE_TTL_MS) {
    return withRequestId(addHeaders(jsonOk({ rows: cached.rows })), requestId);
  }

  let rows: Awaited<ReturnType<typeof fetchEdgeBoard>> = [];
  for (const key of keys) {
    try {
      rows = await fetchEdgeBoard(sport, key);
      break;
    } catch (e) {
      logError(e instanceof Error ? e : new Error(String(e)), { sport, route: "edge-board/today" });
    }
  }
  if (rows.length === 0 && cached) {
    return withRequestId(addHeaders(jsonOk({ rows: cached.rows })), requestId);
  }
  try {
    rows = mergeKeiIntoEdgeBoardRows(rows, sport);
    const parsed = EdgeBoardResponseSchema.safeParse({ rows });
    if (!parsed.success) {
      if (cached) return withRequestId(addHeaders(jsonOk({ rows: cached.rows })), requestId);
      return withRequestId(addHeaders(jsonOk({ rows: [] })), requestId);
    }
    sportCache.set(sport, { rows: parsed.data.rows, ts: now });
    return withRequestId(addHeaders(jsonOk(parsed.data)), requestId);
  } catch (e) {
    logError(e instanceof Error ? e : new Error(String(e)), { sport, route: "edge-board/today" });
    if (cached) return withRequestId(addHeaders(jsonOk({ rows: cached.rows })), requestId);
    return withRequestId(addHeaders(jsonOk({ rows: [] })), requestId);
  }
}
