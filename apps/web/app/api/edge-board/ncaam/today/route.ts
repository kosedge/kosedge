import { NextResponse } from "next/server";
import crypto from "node:crypto";
import { env } from "@/lib/config/env";
import { EdgeBoardResponseSchema } from "@kosedge/contracts";

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

async function tryModelService(
  requestId: string,
): Promise<{ ok: true; rows: unknown[] } | { ok: false }> {
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
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });

    const contentType = res.headers.get("content-type") ?? "";
    const raw = await res.text();

    if (!res.ok || !contentType.includes("application/json"))
      return { ok: false };

    const parsed = EdgeBoardResponseSchema.safeParse(JSON.parse(raw));
    if (!parsed.success) return { ok: false };

    return { ok: true, rows: parsed.data.rows };
  } catch {
    return { ok: false };
  } finally {
    clearTimeout(timeout);
  }
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

  const modelResult = await tryModelService(requestId);
  if (modelResult.ok && modelResult.rows.length > 0) {
    ncaamCache = { rows: modelResult.rows, ts: now };
    return json(
      {
        rows: modelResult.rows,
        source: "snapshot",
        reason: "ok",
        availability: "ok",
      },
      200,
      { "x-request-id": requestId },
    );
  }

  // No Odds API fallback — request path is DENIED.
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
