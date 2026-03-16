import { jsonError, jsonOk } from "@/lib/api/response";
import { ensureInternalSecret, getRequestId, withRequestId } from "@/lib/edge-board-common";
import { env } from "@/lib/config/env";
import { cacheControlHeader, EDGE_BOARD_NCAAM_CACHE_TTL_MS } from "@/lib/constants";
import { logError } from "@/lib/logger";
import { fetchEdgeBoard } from "@/lib/odds-api";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

let ncaamCache: { rows: unknown[]; ts: number } | null = null;

function withCacheHeaders(res: NextResponse): NextResponse {
  res.headers.set("cache-control", cacheControlHeader());
  return res;
}

async function tryModelService(requestId: string): Promise<{ ok: true; rows: unknown[] } | { ok: false }> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) return { ok: false };

  const upstream = `${base.replace(/\/+$/, "")}/edge-board/ncaam/today`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(upstream, {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        "x-request-id": requestId,
        ...(env.INTERNAL_API_SECRET ? { "x-kosedge-secret": env.INTERNAL_API_SECRET } : {}),
      },
    });

    const contentType = res.headers.get("content-type") ?? "";
    const raw = await res.text();

    if (!res.ok || !contentType.includes("application/json")) return { ok: false };

    const parsed = EdgeBoardResponseSchema.safeParse(JSON.parse(raw));
    if (!parsed.success) return { ok: false };

    return { ok: true, rows: parsed.data.rows };
  } catch {
    return { ok: false };
  } finally {
    clearTimeout(timeout);
  }
}

async function tryOddsApiFallback(): Promise<{ ok: true; rows: unknown[] } | { ok: false }> {
  const key = env.ODDS_API_KEY?.trim();
  if (!key) return { ok: false };
  try {
    const rows = await fetchEdgeBoard("ncaam", key);
    return { ok: true, rows };
  } catch (e) {
    console.error("edge_board_odds_fallback_failed", { error: String(e) });
    return { ok: false };
  }
}

export async function GET(req: Request) {
  const requestId = getRequestId(req);

  const unauthorized = ensureInternalSecret(req, requestId);
  if (unauthorized) return unauthorized;

  const now = Date.now();
  if (ncaamCache && now - ncaamCache.ts < EDGE_BOARD_NCAAM_CACHE_TTL_MS) {
    return withRequestId(withCacheHeaders(jsonOk({ rows: ncaamCache.rows })), requestId);
  }

  const modelResult = await tryModelService(requestId);
  if (modelResult.ok && modelResult.rows.length > 0) {
    ncaamCache = { rows: modelResult.rows, ts: now };
    return withRequestId(withCacheHeaders(jsonOk({ rows: modelResult.rows })), requestId);
  }

  const oddsResult = await tryOddsApiFallback();
  if (oddsResult.ok) {
    ncaamCache = { rows: oddsResult.rows, ts: now };
    return withRequestId(withCacheHeaders(jsonOk({ rows: oddsResult.rows })), requestId);
  }

  if (ncaamCache) {
    return withRequestId(withCacheHeaders(jsonOk({ rows: ncaamCache.rows })), requestId);
  }
  return withRequestId(withCacheHeaders(jsonOk({ rows: [] })), requestId);
}