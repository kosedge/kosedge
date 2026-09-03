import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";

export const dynamic = "force-dynamic";

const DEFAULT_SEASON = 2026;
const FETCH_DAYS_AHEAD = 200;
const PAST_WEEK_DAYS = 7;

/**
 * Page-data for /pro/nfl/fair-lines.
 * Client-fetch so HTML completion is not blocked on model-service (Alex).
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

  const board = await fetchNflFairLines({
    season,
    daysAhead: FETCH_DAYS_AHEAD,
    includePastDays,
  });

  return NextResponse.json(board);
}
