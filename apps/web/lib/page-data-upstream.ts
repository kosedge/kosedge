import { NextResponse } from "next/server";
import { pageDataCacheHeaders } from "@/lib/page-data-cache";
import { UpstreamTimeoutError } from "@/lib/upstream-fetch";

/**
 * Map upstream timeout/transport failures to 503/504 for page-data APIs.
 * Never return HTTP 200 with an empty slate that looks like a real board.
 * Never cache 503/504 (Cache-Control: private, no-store).
 */
export function pageDataUpstreamErrorResponse(err: unknown): NextResponse {
  const noStore = pageDataCacheHeaders({ cacheable: false });
  if (err instanceof UpstreamTimeoutError) {
    return NextResponse.json(
      { error: "Upstream timed out.", timeoutMs: err.timeoutMs },
      { status: 504, headers: noStore },
    );
  }
  const message =
    err instanceof Error && err.message.trim()
      ? err.message
      : "Unable to reach model service.";
  return NextResponse.json(
    { error: message },
    { status: 503, headers: noStore },
  );
}
