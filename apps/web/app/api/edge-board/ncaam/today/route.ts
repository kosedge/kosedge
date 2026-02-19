import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";
import { fetchEdgeBoard } from "@/lib/odds-api";

export const dynamic = "force-dynamic";

/** Odds refresh at most every 6 hours to limit API usage */
const ODDS_CACHE_TTL_MS = 6 * 60 * 60 * 1000;
const CACHE_HEADERS = {
  "cache-control": "public, s-maxage=21600, stale-while-revalidate=3600",
};

let ncaamCache: { rows: unknown[]; ts: number } | null = null;

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

  const expected = env.INTERNAL_API_SECRET;
  if (expected) {
    const provided = req.headers.get("x-kosedge-secret");
    if (provided !== expected) {
      return json({ error: "Unauthorized", requestId }, 401, { "x-request-id": requestId });
    }
  }

  const now = Date.now();
  if (ncaamCache && now - ncaamCache.ts < ODDS_CACHE_TTL_MS) {
    return json({ rows: ncaamCache.rows }, 200, { "x-request-id": requestId });
  }

  // 1. Try model service first
  const modelResult = await tryModelService(requestId);
  if (modelResult.ok && modelResult.rows.length > 0) {
    ncaamCache = { rows: modelResult.rows, ts: now };
    return json({ rows: modelResult.rows }, 200, { "x-request-id": requestId });
  }

  // 2. Fallback to Odds API when model not available
  const oddsResult = await tryOddsApiFallback();
  if (oddsResult.ok) {
    ncaamCache = { rows: oddsResult.rows, ts: now };
    return json({ rows: oddsResult.rows }, 200, { "x-request-id": requestId });
  }

  if (ncaamCache) {
    return json({ rows: ncaamCache.rows }, 200, { "x-request-id": requestId });
  }
  return json({ rows: [] }, 200, { "x-request-id": requestId });
}