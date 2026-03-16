// apps/web/lib/edge-board-common.ts
import crypto from "node:crypto";
import { NextResponse } from "next/server";
import { env } from "@/lib/config/env";

export function getRequestId(req: Request): string {
  return (
    req.headers.get("x-request-id") ||
    req.headers.get("x-correlation-id") ||
    crypto.randomUUID()
  );
}

export function withRequestId<T extends NextResponse>(
  res: T,
  requestId: string
): T {
  res.headers.set("x-request-id", requestId);
  return res;
}

/**
 * Enforce INTERNAL_API_SECRET if configured.
 * Returns an Unauthorized response when the secret is invalid; otherwise null.
 */
export function ensureInternalSecret(
  req: Request,
  requestId: string
): NextResponse | null {
  const expected = env.INTERNAL_API_SECRET;
  if (!expected) return null;

  const provided = req.headers.get("x-kosedge-secret");
  if (provided === expected) return null;

  const res = NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  return withRequestId(res, requestId);
}

