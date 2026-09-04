import { NextResponse } from "next/server";
import { PAGE_DATA_NO_STORE } from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
/** Cron warm budget ≤40s — fetch existing assemble SoT only; never invent board rows. */
export const maxDuration = 40;

/**
 * #12 GO-1c — optional CDN warm for Edge Board assemble.
 * Hits public page-data assemble routes so Vercel can store HIT for the 45s band.
 * Does not remat, invent SoT, or mint as-of clocks.
 */
const WARM_PATHS = [
  "/api/edge-board/nfl/assemble?slate=week1",
  "/api/edge-board/cfb/assemble?week=1",
] as const;

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
    ms: number;
  }> = [];

  for (const path of WARM_PATHS) {
    const started = Date.now();
    try {
      const res = await fetch(`${origin}${path}`, {
        method: "GET",
        headers: {
          // Identify warm traffic; rate-limit skips x-vercel-cron / cron bearer.
          "x-kosedge-warm": "1",
          ...(process.env.CRON_SECRET
            ? { authorization: `Bearer ${process.env.CRON_SECRET}` }
            : {}),
        },
        cache: "no-store",
      });
      results.push({
        path,
        status: res.status,
        cacheControl: res.headers.get("cache-control"),
        cdnCacheControl: res.headers.get("cdn-cache-control"),
        vercelCache: res.headers.get("x-vercel-cache"),
        ms: Date.now() - started,
      });
    } catch (err) {
      results.push({
        path,
        status: 0,
        cacheControl: null,
        cdnCacheControl: null,
        vercelCache: null,
        ms: Date.now() - started,
      });
      void err;
    }
  }

  return NextResponse.json(
    {
      ok: true,
      warmed: results,
      note: "Warm only — assemble SoT unchanged; as-of stays book vintage.",
    },
    {
      status: 200,
      headers: { "Cache-Control": PAGE_DATA_NO_STORE },
    },
  );
}
