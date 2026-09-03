import { NextResponse } from "next/server";
import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  loadAssembledEdgeBoardRows,
  normalizeNflEdgeBoardSlate,
} from "@/lib/build-edge-board-rows";
import { filterNflStrictWeekRows } from "@/lib/nfl-edge-board-from-fair-lines";
import {
  ensureNflScheduleWeekOnBoard,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import { pickLatestIso } from "@/lib/market-asof-stamp";
import { getSport } from "@/lib/sports";

export const dynamic = "force-dynamic";

/**
 * Public page-data for Edge Board.
 * HTML shells client-fetch this so document completion is not blocked on
 * model-service / Odds (Alex: SSR wait waterfall, not download).
 * No INTERNAL_API_SECRET — same rows the public /edge-board page already shows.
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

  try {
    if (sport === "nfl") {
      // One full assemble (Odds ∥ fair-lines inside), then derive Week 1 — same as prior SSR.
      const fullRows = ensureNflScheduleWeekOnBoard(
        stampNflEdgeBoardWeeksFromSchedule(
          await loadAssembledEdgeBoardRows("nfl", { slate: "full" }),
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
      const linesAsOf = pickLatestIso(
        ...rows.map((r) => (r as { linesAsOf?: string }).linesAsOf),
      );
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
        await loadAssembledEdgeBoardRows("cfb", { slate: "week1" }),
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

    const rows = await loadAssembledEdgeBoardRows(sport, { slate: "week1" });
    return NextResponse.json({
      rows,
      week0Count: 0,
      week1Count: 0,
      fullCount: 0,
      weeks: [],
      linesAsOf: null,
      games: gameCount(rows),
    });
  } catch {
    return NextResponse.json({
      rows: [],
      week0Count: 0,
      week1Count: 0,
      fullCount: 0,
      weeks: [],
      linesAsOf: null,
      games: 0,
      error: "Unable to assemble edge board.",
    });
  }
}
