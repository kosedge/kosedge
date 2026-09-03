import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";

export const dynamic = "force-dynamic";
/** Client-fetched page-data — may wait on cold Railway beyond Overview board cap. */
export const maxDuration = 30;

const DEFAULT_SEASON = 2026;
const FETCH_DAYS_AHEAD = 200;
const PAST_WEEK_DAYS = 7;

/**
 * Page-data for /pro/nfl/fair-lines.
 * Client-fetch so HTML completion is not blocked on model-service (Alex).
 * Uses pageData timeout (25s); transport failures → 503/504 (not fake empty 200).
 */
export async function GET(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const seasonRaw = Number(url.searchParams.get("season"));
  const season =
    Number.isFinite(seasonRaw) && seasonRaw >= 2010
      ? seasonRaw
      : DEFAULT_SEASON;
  const includePastRaw = url.searchParams.get("includePast");
  const includePastDays =
    includePastRaw === "7" || includePastRaw === "3" || includePastRaw === "1"
      ? PAST_WEEK_DAYS
      : 0;

  try {
    const board = await fetchNflFairLines({
      season,
      daysAhead: FETCH_DAYS_AHEAD,
      includePastDays,
      timeoutMs: UPSTREAM_TIMEOUT_MS.pageData,
      throwOnTransportError: true,
    });
    return NextResponse.json(board);
  } catch (err) {
    return pageDataUpstreamErrorResponse(err);
  }
}
