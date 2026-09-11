import { NextResponse } from "next/server";
import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  loadAssembledEdgeBoardRows,
  normalizeNflEdgeBoardSlate,
} from "@/lib/build-edge-board-rows";
import { scrubEdgeBoardAssembleCustomerRows } from "@/lib/edge-board-assemble-quarantine";
import {
  filterNflStrictWeekRows,
  resolveEdgeBoardBoardLinesAsOf,
} from "@/lib/nfl-edge-board-from-fair-lines";
import {
  ensureNflScheduleWeekOnBoard,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { requireGovernedNflFullSlate } from "@/lib/nfl-edge-board-assemble-window";
import {
  parseCfbAssembleWeek,
  scopeCfbLiveEdgeBoardRows,
} from "@/lib/cfb-edge-board-week";
import { stampCfbEdgeBoardWeek } from "@/lib/cfb-kei-artifacts";
import {
  pageDataCacheHeaders,
  pageDataJsonResponse,
} from "@/lib/page-data-cache";
import { pageDataUpstreamErrorResponse } from "@/lib/page-data-upstream";
import { getSport } from "@/lib/sports";
import { isRetiredNcaamSportKey } from "@/lib/ncaam/identity";
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
 * Cache-Control + CDN-Cache-Control s-maxage=45 on non-empty 200 only
 * (never 503/504/games=0). Dual header: Vercel strips s-maxage from
 * Cache-Control alone — see page-data-cache.ts / GO-1c ops note.
 *
 * INC-2026-09-07 (C): Week 1 live assemble uses a narrow window. Full slate
 * serves governed cache/snapshot only — never live daysAhead=200. Missing
 * snapshot → fail closed 503. pageData ceiling stays 25s.
 */
function gameCount(rows: EdgeBoardRow[]): number {
  return new Set(rows.map((r) => r.game).filter(Boolean)).size;
}

function weeksOnBoard(rows: EdgeBoardRow[]): number[] {
  return [
    ...new Set(
      rows
        .map((r) => (r as { week?: number }).week)
        .filter(
          (w): w is number => typeof w === "number" && Number.isFinite(w),
        ),
    ),
  ].sort((a, b) => a - b);
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ sport: string }> },
) {
  const { sport: raw } = await params;
  const sport = (raw || "").toLowerCase();
  // Canonical college-basketball key is `ncaam` only — retire `cbb` / `ncaab`.
  if (isRetiredNcaamSportKey(sport)) {
    return NextResponse.json(
      {
        error: "Retired sport key",
        sport,
        use: "ncaam",
        message: "Use sport=ncaam; cbb/ncaab are retired as API sport keys.",
      },
      { status: 400, headers: pageDataCacheHeaders({ cacheable: false }) },
    );
  }
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
    sport === "cfb" ? parseCfbAssembleWeek(url.searchParams.get("week")) : 1;

  const assembleOpts = {
    timeoutMs: UPSTREAM_TIMEOUT_MS.pageData,
    throwOnTransportError: true as const,
  };

  try {
    if (sport === "nfl") {
      // Cache key includes ?slate= — week1 and full must never share a body.
      if (slate === "full") {
        // INC-2026-09-07 (C): governed snapshot only — never live daysAhead=200.
        // Missing snapshot → throw → 503 fail closed (pageDataUpstreamErrorResponse).
        const governed = requireGovernedNflFullSlate();
        const assembled = ensureNflScheduleWeekOnBoard(
          stampNflEdgeBoardWeeksFromSchedule(governed.rows),
          1,
        );
        const week1Rows = filterNflStrictWeekRows(assembled, 1);
        const linesAsOf =
          resolveEdgeBoardBoardLinesAsOf(assembled) ?? governed.linesAsOf;
        return pageDataJsonResponse({
          rows: scrubEdgeBoardAssembleCustomerRows(assembled),
          week1Count: gameCount(week1Rows),
          fullCount: gameCount(assembled),
          week0Count: 0,
          weeks: weeksOnBoard(assembled),
          linesAsOf,
          games: gameCount(assembled),
          // Observe-friendly provenance (not invent as-of).
          fullSlateSource: governed.source,
        });
      }

      // Week 1 / live: narrow fair-lines window only.
      const assembled = ensureNflScheduleWeekOnBoard(
        stampNflEdgeBoardWeeksFromSchedule(
          await loadAssembledEdgeBoardRows("nfl", {
            slate: "week1",
            ...assembleOpts,
          }),
        ),
        1,
      );
      const week1Rows = filterNflStrictWeekRows(assembled, 1);
      const weeks = weeksOnBoard(week1Rows);
      const linesAsOf = resolveEdgeBoardBoardLinesAsOf(week1Rows);
      return pageDataJsonResponse({
        rows: scrubEdgeBoardAssembleCustomerRows(week1Rows),
        week1Count: gameCount(week1Rows),
        // Week1 responses omit full badge until Full tab opens (honest).
        fullCount: 0,
        week0Count: 0,
        weeks,
        linesAsOf,
        games: gameCount(week1Rows),
      });
    }

    if (sport === "cfb") {
      const all = stampCfbEdgeBoardWeek(
        await loadAssembledEdgeBoardRows("cfb", {
          slate: "week1",
          ...assembleOpts,
        }),
      );
      const live = scopeCfbLiveEdgeBoardRows(all, cfbWeek);
      // Same honesty as NFL: book last_update / row linesAsOf — never GET clock.
      // Missing requested week → empty board (never coerce to week 1).
      // Completed / already-started games are dropped server-side.
      const linesAsOf = resolveEdgeBoardBoardLinesAsOf(live);
      const week0Count = gameCount(scopeCfbLiveEdgeBoardRows(all, 0));
      const week1Count = gameCount(scopeCfbLiveEdgeBoardRows(all, 1));
      const week2Count = gameCount(scopeCfbLiveEdgeBoardRows(all, 2));
      const requestedWeekCount = gameCount(live);
      return pageDataJsonResponse({
        rows: scrubEdgeBoardAssembleCustomerRows(live),
        week0Count,
        week1Count,
        week2Count,
        requestedWeek: cfbWeek,
        requestedWeekCount,
        fullCount: 0,
        weeks: weeksOnBoard(all),
        linesAsOf,
        games: requestedWeekCount,
      });
    }

    const rows = await loadAssembledEdgeBoardRows(sport, {
      slate: "week1",
      ...assembleOpts,
    });
    // Book last_update / row linesAsOf — never GET clock (same honesty as NFL/CFB).
    const linesAsOf = resolveEdgeBoardBoardLinesAsOf(rows);
    return pageDataJsonResponse({
      rows: scrubEdgeBoardAssembleCustomerRows(rows),
      week0Count: 0,
      week1Count: 0,
      fullCount: 0,
      weeks: [],
      linesAsOf,
      games: gameCount(rows),
    });
  } catch (err) {
    return pageDataUpstreamErrorResponse(err);
  }
}
