import { NextResponse } from "next/server";
import { getProAccessState } from "@/lib/auth/pro";
import { toFairLinesApiBoard } from "@/lib/fair-lines-api-board";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import {
  pageDataCacheHeaders,
  pageDataJsonResponse,
} from "@/lib/page-data-cache";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * Page-data for /pro/mlb/fair-lines.
 * Proxies model-service; empty slate stays empty (asOf/oddsAsOf null — never invent).
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

  // Soft-empty on transport — prefer honest 200 over bare 404 for Pro desks.
  const board = await fetchMlbFairLines({ gameDate });
  return pageDataJsonResponse(
    toFairLinesApiBoard({
      sport: "mlb",
      sportLabel: "MLB",
      lines: board.lines,
      modelVersion: board.modelVersion,
      gameDate: board.gameDate,
      // MLB upstream does not emit as_of / odds_as_of today — leave null.
      asOf: null,
      oddsAsOf: null,
      slateStatus: board.error
        ? "upstream_error"
        : board.lines.length === 0
          ? "no_slate"
          : "ok",
      error: board.error,
      message: board.error
        ? `MLB fair-lines upstream unavailable. We do not invent book prices.`
        : undefined,
    }),
  );
}
