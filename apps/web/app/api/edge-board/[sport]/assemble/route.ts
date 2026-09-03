import { NextResponse } from "next/server";
import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  loadAssembledEdgeBoardRows,
  normalizeNflEdgeBoardSlate,
} from "@/lib/build-edge-board-rows";
import {
  filterNflStrictWeekRows,
  resolveEdgeBoardBoardLinesAsOf,
} from "@/lib/nfl-edge-board-from-fair-lines";
import {
  ensureNflScheduleWeekOnBoard,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import { getSport } from "@/lib/sports";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";

export const dynamic = "force-dynamic";
/** Client-fetched page-data — may wait on cold Railway beyond Overview board cap. */
export const maxDuration = 30;

/**
 * Public page-data for Edge Board.
 * HTML shells client-fetch this so document completion is not blocked on
 * model-service / Odds (Alex: SSR wait waterfall, not download).
 * No INTERNAL_API_SECRET — same rows the public /edge-board page already shows.
 * NFL fair-lines transport failures → 503/504 (not partial KEI pack without vintage).
 */
function gameCount(rows: EdgeBoardRow[]): number {
  return new Set(rows.map((r) => r.game).filter(Boolean)).size;
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ sport: string }> },
) {
  const { sport: raw } = await params;
  const sport = (raw || "").toLowerCase();
  if (!getSport(sport)) {
    return NextResponse.json(
      { error: "Unknown sport", sport },
      { status: 400 },
    );
  }

  const url = new URL(req.url);
  const slate =
    sport === "nfl"
      ? normalizeNflEdgeBoardSlate(url.searchParams.get("slate"))
      : "week1";
  const cfbWeek =
    sport === "cfb" && url.searchParams.get("week") === "0" ? 0 : 1;

  const assembleOpts = {
    timeoutMs: UPSTREAM_TIMEOUT_MS.pageData,
    throwOnTransportError: true as const,
  };

  try {
    if (sport === "nfl") {
      // One full assemble (Odds ∥ fair-lines inside), then derive Week 1 — same as prior SSR.
      const fullRows = ensureNflScheduleWeekOnBoard(
        stampNflEdgeBoardWeeksFromSchedule(
          await loadAssembledEdgeBoardRows("nfl", {
            slate: "full",
            ...assembleOpts,
          }),
        ),
        1,
      );
      const week1Rows = filterNflStrictWeekRows(fullRows, 1);
      const rows = slate === "full" ? fullRows : week1Rows;
      const weeks = [
        ...new Set(
          rows
            .map((r) => (r as { week?: number }).week)
            .filter(
              (w): w is number => typeof w === "number" && Number.isFinite(w),
            ),
        ),
      ].sort((a, b) => a - b);
      const linesAsOf = resolveEdgeBoardBoardLinesAsOf(rows);
      return NextResponse.json({
        rows,
        week1Count: gameCount(week1Rows),
        fullCount: gameCount(fullRows),
        week0Count: 0,
        weeks,
        linesAsOf,
        games: gameCount(rows),
      });
    }

    if (sport === "cfb") {
      const all = stampCfbEdgeBoardWeek(
        await loadAssembledEdgeBoardRows("cfb", {
          slate: "week1",
          ...assembleOpts,
        }),
      );
      const rows = all.filter((r) => r.week === cfbWeek);
      return NextResponse.json({
        rows,
        week0Count: gameCount(all.filter((r) => r.week === 0)),
        week1Count: gameCount(all.filter((r) => r.week === 1)),
        fullCount: 0,
        weeks: [],
        linesAsOf: null,
        games: gameCount(rows),
      });
    }

    const rows = await loadAssembledEdgeBoardRows(sport, {
      slate: "week1",
      ...assembleOpts,
    });
    return NextResponse.json({
      rows,
      week0Count: 0,
      week1Count: 0,
      fullCount: 0,
      weeks: [],
      linesAsOf: null,
      games: gameCount(rows),
    });
  } catch (err) {
    return pageDataUpstreamErrorResponse(err);
  }
}
