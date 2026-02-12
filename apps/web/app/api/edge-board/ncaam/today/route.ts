// apps/web/app/api/edge-board/ncaam/today/route.ts
import { NextResponse } from "next/server";
import { env } from "@/lib/config/env";

export const dynamic = "force-dynamic";

/**
 * Small helper: JSON response with consistent headers.
 */
function json(data: unknown, status = 200) {
  return NextResponse.json(data, {
    status,
    headers: {
      "cache-control": "no-store, no-cache, must-revalidate, proxy-revalidate",
      pragma: "no-cache",
      expires: "0",
    },
  });
}

export async function GET(req: Request) {
  // 1) Optional internal auth gate (recommended for production)
  const expected = env.INTERNAL_API_SECRET;

  if (expected) {
    const provided = req.headers.get("x-kosedge-secret");
    if (provided !== expected) {
      return json({ error: "Unauthorized" }, 401);
    }
  }

  // 2) Validate config
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return json({ error: "MODEL_SERVICE_URL is not set" }, 500);
  }

  const upstream = `${base.replace(/\/+$/, "")}/edge-board/ncaam/today`;

  // 3) Fetch with timeout
  const controller = new AbortController();
  const timeoutMs = 8000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(upstream, {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        // Optional: forward secret downstream if your model-service also supports it
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });

    // Read body safely (even if non-JSON)
    const contentType = res.headers.get("content-type") ?? "";
    const raw = await res.text();

    if (!res.ok) {
      return json(
        {
          error: "Upstream error",
          upstreamStatus: res.status,
          upstreamUrl: upstream,
          body: raw.slice(0, 2000), // keep logs sane
        },
        502
      );
    }

    // Parse JSON (prefer JSON, but fail gracefully)
    if (!contentType.includes("application/json")) {
      return json(
        {
          error: "Upstream returned non-JSON",
          upstreamUrl: upstream,
          contentType,
          body: raw.slice(0, 2000),
        },
        502
      );
    }

    const data = JSON.parse(raw) as unknown;
    return json(data, 200);
  } catch (e: unknown) {
    const message =
      e instanceof Error ? e.message : typeof e === "string" ? e : "Unknown error";

    const isAbort =
      e instanceof Error && (e.name === "AbortError" || message.toLowerCase().includes("aborted"));

    return json(
      {
        error: isAbort ? "Upstream timeout" : "Proxy failed",
        detail: message,
        upstreamUrl: upstream,
      },
      502
    );
  } finally {
    clearTimeout(timeout);
  }
}