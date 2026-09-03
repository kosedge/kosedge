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
import {
  pageDataCacheHeaders,
  pageDataJsonResponse,
} from "@/lib/page-data-cache";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import { getSport } from "@/lib/sports";
import { UPSTREAM_TIMEOUT_MS } from "@/lib/upstream-fetch";
import {
  displaySuppressionNoteForUi,
  isGameConfidenceBandDisplayOff,
  loadDisplayHonestyFlags,
} from "@/lib/display-honesty";

export const dynamic = "force-dynamic";
/** Client-fetched page-data — may wait on cold Railway beyond Overview board cap. */
export const maxDuration = 30;

/**
 * Public page-data for Edge Board.
 * HTML shells client-fetch this so document completion is not blocked on
 * model-service / Odds (Alex: SSR wait waterfall, not download).
 * No INTERNAL_API_SECRET — same rows the public /edge-board page already shows.
 * NFL fair-lines transport failures → 503/504 (not partial KEI pack without vintage).
 * Cache-Control s-maxage=45 on non-empty 200 only (never 503/504/games=0).
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
      { status: 400, headers: pageDataCacheHeaders({ cacheable: false }) },
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
    const displayFlags = await loadDisplayHonestyFlags();
    const displayHonesty = {
      nfl_game_confidence_band_display:
        displayFlags.nfl_game_confidence_band_display,
      display_suppression_note: displaySuppressionNoteForUi(displayFlags),
      suppressGameConfidenceBand: isGameConfidenceBandDisplayOff(displayFlags),
    };

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
      return pageDataJsonResponse({
        rows,
        week1Count: gameCount(week1Rows),
        fullCount: gameCount(fullRows),
        week0Count: 0,
        weeks,
        linesAsOf,
        games: gameCount(rows),
        displayHonesty,
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
      return pageDataJsonResponse({
        rows,
        week0Count: gameCount(all.filter((r) => r.week === 0)),
        week1Count: gameCount(all.filter((r) => r.week === 1)),
        fullCount: 0,
        weeks: [],
        linesAsOf: null,
        games: gameCount(rows),
        displayHonesty,
      });
    }

    const rows = await loadAssembledEdgeBoardRows(sport, {
      slate: "week1",
      ...assembleOpts,
    });
    return pageDataJsonResponse({
      rows,
      week0Count: 0,
      week1Count: 0,
      fullCount: 0,
      weeks: [],
      linesAsOf: null,
      games: gameCount(rows),
      displayHonesty,
    });
  } catch (err) {
    return pageDataUpstreamErrorResponse(err);
  }
}
