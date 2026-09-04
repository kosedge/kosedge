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
    sport === "cfb" && url.searchParams.get("week") === "0" ? 0 : 1;

  const assembleOpts = {
    timeoutMs: UPSTREAM_TIMEOUT_MS.pageData,
    throwOnTransportError: true as const,
  };

  try {
    if (sport === "nfl") {
      // #12 GO-1: honor requested slate — week1 must not enrich the full slate
      // just for a tab badge (COLD hydrate paid full-slate CPU after Railway).
      // Odds ∥ fair-lines still parallel inside loadAssembled.
      const assembled = ensureNflScheduleWeekOnBoard(
        stampNflEdgeBoardWeeksFromSchedule(
          await loadAssembledEdgeBoardRows("nfl", {
            slate,
            ...assembleOpts,
          }),
        ),
        1,
      );
      const week1Rows = filterNflStrictWeekRows(assembled, 1);
      const rows = slate === "full" ? assembled : week1Rows;
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
        // #8 Phase C / NFL-V3 — strip quarantine vocab from customer assemble.
        rows: scrubEdgeBoardAssembleCustomerRows(rows),
        week1Count: gameCount(week1Rows),
        // Full-slate badge count only when this response is the full assemble.
        // Week1 responses omit the badge number until Full tab is opened (honest).
        fullCount: slate === "full" ? gameCount(assembled) : 0,
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
      // Same honesty as NFL: book last_update / row linesAsOf — never GET clock.
      const linesAsOf = resolveEdgeBoardBoardLinesAsOf(rows);
      return pageDataJsonResponse({
        rows: scrubEdgeBoardAssembleCustomerRows(rows),
        week0Count: gameCount(all.filter((r) => r.week === 0)),
        week1Count: gameCount(all.filter((r) => r.week === 1)),
        fullCount: 0,
        weeks: [],
        linesAsOf,
        games: gameCount(rows),
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
