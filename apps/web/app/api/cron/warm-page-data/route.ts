import { NextResponse } from "next/server";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
/** Cron warm budget ≤40s — fetch existing assemble SoT only; never invent board rows. */
export const maxDuration = 40;

/**
 * #12 GO-1c / INC-2026-09-07 (E) — optional CDN warm for Edge Board assemble.
 * Hits authentic **public** page-data assemble routes (no Authorization on the
 * warm GET) so Vercel stores HIT for the 45s band instead of CDN BYPASS.
 * Bounded paths only (NFL week1 + CFB current-week default). Does not remat, invent SoT,
 * mint as-of clocks, or warm full-slate (avoids uncontrolled Odds spend).
 */
const WARM_PATHS = [
  "/api/edge-board/nfl/assemble?slate=week1",
  "/api/edge-board/cfb/assemble",
] as const;

/** Soft alert when warm misses the public cache path or origin is unhealthy. */
export type WarmAlertReason =
  | "origin_error"
  | "cdn_bypass"
  | "cache_miss"
  | null;

function authorizeCron(req: Request): boolean {
  const secret = process.env.CRON_SECRET?.trim();
  if (secret) {
    // Vercel Cron sends Authorization: Bearer <CRON_SECRET> when configured.
    return (req.headers.get("authorization") || "") === `Bearer ${secret}`;
  }
  // Local / unset: allow only when not production.
  return process.env.NODE_ENV !== "production";
}

function originFrom(req: Request): string {
  // Prefer production host so CDN warm hits the same cache key users use.
  const configured =
    process.env.PAGE_DATA_WARM_ORIGIN?.trim() ||
    process.env.SITE_URL?.trim() ||
    process.env.AUTH_URL?.trim() ||
    process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (configured) {
    try {
      return new URL(configured).origin;
    } catch {
      /* fall through */
    }
  }
  if (process.env.VERCEL_ENV === "production") {
    return "https://www.kosedge.com";
  }
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`;
  }
  return new URL(req.url).origin;
}

function classifyWarmAlert(args: {
  status: number;
  vercelCache: string | null;
}): WarmAlertReason {
  if (args.status === 0 || args.status >= 500) return "origin_error";
  const cache = (args.vercelCache || "").toUpperCase();
  if (cache === "BYPASS") return "cdn_bypass";
  if (cache === "MISS") return "cache_miss";
  return null;
}

export async function GET(req: Request) {
  if (!authorizeCron(req)) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401, headers: { "Cache-Control": PAGE_DATA_NO_STORE } },
    );
  }

  const origin = originFrom(req);
  const results: Array<{
    path: string;
    status: number;
    cacheControl: string | null;
    cdnCacheControl: string | null;
    vercelCache: string | null;
    age: string | null;
    ms: number;
    alert: WarmAlertReason;
  }> = [];

  for (const path of WARM_PATHS) {
    const started = Date.now();
    try {
      // Public cache path: do NOT forward CRON_SECRET Authorization — that
      // forces Vercel CDN BYPASS and defeats the warm. Auth stays on this
      // cron route only. x-kosedge-warm skips rate-limit without BYPASS.
      const res = await fetch(`${origin}${path}`, {
        method: "GET",
        headers: {
          "x-kosedge-warm": "1",
          accept: "application/json",
        },
      });
      const vercelCache = res.headers.get("x-vercel-cache");
      const status = res.status;
      results.push({
        path,
        status,
        cacheControl: res.headers.get("cache-control"),
        cdnCacheControl: res.headers.get("cdn-cache-control"),
        vercelCache,
        age: res.headers.get("age"),
        ms: Date.now() - started,
        alert: classifyWarmAlert({ status, vercelCache }),
      });
    } catch (err) {
      results.push({
        path,
        status: 0,
        cacheControl: null,
        cdnCacheControl: null,
        vercelCache: null,
        age: null,
        ms: Date.now() - started,
        alert: "origin_error",
      });
      void err;
    }
  }

  const alerts = results
    .filter((r) => r.alert != null)
    .map((r) => ({
      path: r.path,
      alert: r.alert,
      status: r.status,
      vercelCache: r.vercelCache,
    }));

  // Origin healthy + no CDN BYPASS. First-hit MISS is expected while populating.
  const ok =
    results.every((r) => r.status >= 200 && r.status < 500) &&
    results.every(
      (r) => r.alert !== "cdn_bypass" && r.alert !== "origin_error",
    );

  return NextResponse.json(
    {
      ok,
      warmed: results,
      alerts,
      freshness: {
        // Observe-friendly: repeated warms should flip MISS→HIT within 45s.
        note: "Public path warm — no Authorization on assemble GET; cache key = path+query (sport/slate/week).",
      },
      note: "Warm only — assemble SoT unchanged; as-of stays book vintage; full-slate not warmed (Odds spend bound).",
    },
    {
      status: 200,
      headers: { "Cache-Control": PAGE_DATA_NO_STORE },
    },
  );
}
