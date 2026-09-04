import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { toFairLinesApiBoard } from "@/lib/fair-lines-api-board";
import { fetchNhlFairLines } from "@/lib/nhl-fair-lines";
import {
  pageDataCacheHeaders,
  pageDataJsonResponse,
} from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * Page-data for /pro/nhl/fair-lines.
 * Proxies model-service; offseason/empty stays honest (no invented puck lines).
 */
export async function GET(req: Request) {
  const access = await getProAccessState();
  if (access !== "authorized") {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401, headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }

  const url = new URL(req.url);
  const gameDate = url.searchParams.get("date") ?? undefined;
  const daysAheadRaw = Number(url.searchParams.get("daysAhead"));
  const daysAhead =
    Number.isFinite(daysAheadRaw) && daysAheadRaw > 0 ? daysAheadRaw : 7;

  const board = await fetchNhlFairLines({ gameDate, daysAhead });
  return pageDataJsonResponse(
    toFairLinesApiBoard({
      sport: "nhl",
      sportLabel: "NHL",
      lines: board.lines,
      modelVersion: board.modelVersion,
      gameDate: board.gameDate,
      asOf: null,
      oddsAsOf: null,
      slateStatus: board.slateStatus,
      message: board.message,
      error: board.error,
    }),
  );
}
