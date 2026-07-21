/**
 * Shared edge-board assembly.
 * NFL: pulls fair-lines + Odds API, persists odds via model-service fair-lines,
 * Live = current week slate, Full = all games with sportsbook odds.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  ensureAllKeiGamesOnBoard,
  mergeKeiIntoEdgeBoardRows,
} from "@/lib/edge-board-kei";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { ALLOWED_BOOKS, fetchEdgeBoard } from "@/lib/odds-api";
import {
  fairLinesToEdgeBoardRows,
  filterNflCurrentWeekRows,
  filterNflOddsPostedRows,
  overlayOddsOntoFairLineRows,
  sortNflEdgeBoardRows,
} from "@/lib/nfl-edge-board-from-fair-lines";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { getKeiLines, type KeiLineGame } from "@/lib/kei-lines";
import {
  keiGamesFromNflFairLines,
  resolveKeiGames,
} from "@/lib/resolve-kei-lines";

const NFL_EDGE_BOARD_SEASON = 2026;

export type AssembleEdgeBoardOptions = {
  /** NFL: `live` = current week; `all` = every game with sportsbook odds. */
  slate?: "live" | "all";
};

function countPriced(rows: EdgeBoardRow[]): number {
  return rows.filter((r) => Boolean(r.best || r.open)).length;
}

async function pullNflOddsRows(): Promise<EdgeBoardRow[]> {
  const keys = getOddsApiKeys();
  for (const key of keys) {
    try {
      const rows = await fetchEdgeBoard("nfl", key);
      if (rows.length > 0) return rows;
    } catch {
      // try next key
    }
  }
  return [];
}

async function assembleNflEdgeBoardRows(
  oddsRows: EdgeBoardRow[],
  options?: AssembleEdgeBoardOptions,
): Promise<EdgeBoardRow[]> {
  const slate = options?.slate ?? "live";

  const pulledOdds = await pullNflOddsRows();
  const odds =
    countPriced(pulledOdds) >= countPriced(oddsRows) ? pulledOdds : oddsRows;

  // Fair-lines pull also persists Odds API events into odds_snapshots for training.
  const fair = await fetchNflFairLines({
    season: NFL_EDGE_BOARD_SEASON,
    daysAhead: 200,
    includePastDays: 14,
    bookmakers: ALLOWED_BOOKS.join(","),
  });

  let keiGames: KeiLineGame[] = [];
  let rows: EdgeBoardRow[] = [];
  const currentWeek = fair.currentWeek || 1;

  if (fair.lines.length > 0) {
    keiGames = keiGamesFromNflFairLines(fair.lines);
    rows = fairLinesToEdgeBoardRows(fair.lines);
    rows = overlayOddsOntoFairLineRows(rows, odds);
  } else {
    keiGames = getKeiLines("nfl");
    rows = ensureAllKeiGamesOnBoard(odds, "nfl", keiGames);
    rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
    rows = sortNflEdgeBoardRows(rows);
    return slate === "live"
      ? filterNflOddsPostedRows(rows)
      : filterNflOddsPostedRows(rows);
  }

  rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
  rows = sortNflEdgeBoardRows(rows);

  if (slate === "live") {
    return filterNflCurrentWeekRows(rows, currentWeek);
  }
  // Full season tab: everything we currently have sportsbook odds on.
  return filterNflOddsPostedRows(rows);
}

export async function assembleEdgeBoardRows(
  sportKey: string,
  oddsRows: EdgeBoardRow[],
  options?: AssembleEdgeBoardOptions,
): Promise<EdgeBoardRow[]> {
  if (sportKey.toLowerCase() === "nfl") {
    return assembleNflEdgeBoardRows(oddsRows, options);
  }

  const keiGames = await resolveKeiGames(sportKey);
  const seeded = ensureAllKeiGamesOnBoard(oddsRows, sportKey, keiGames);
  return mergeKeiIntoEdgeBoardRows(seeded, sportKey, keiGames);
}
