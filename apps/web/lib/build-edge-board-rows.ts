/**
 * Shared edge-board assembly.
 * NFL: pulls fair-lines + Odds API, persists odds via model-service fair-lines,
 * Live = current week slate, Full = all games with sportsbook odds.
 * MLB: seeds from model-service fair-lines when Odds is empty (real model vs KEI).
 * NBA/WNBA: fair-lines → KEI handicap (model_* identity until pre_blend exists).
 * NCAAM: Odds + kei_lines_ncaam.json.
 * NHL / CFB: **markets-only** until a KEI model ships — Odds/fallback only;
 *   resolveKeiGames returns [] (do not invent KEI). UI banners via
 *   sportIsMarketsOnlyEdgeBoard.
 * Never invents sportsbook or KEI prices; empty offseason boards stay empty honestly.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  ensureAllKeiGamesOnBoard,
  mergeKeiIntoEdgeBoardRows,
} from "@/lib/edge-board-kei";
import { loadEdgeBoardFallback } from "@/lib/edge-board-fallback";
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

async function pullOddsRows(sport: string): Promise<EdgeBoardRow[]> {
  const keys = getOddsApiKeys();
  for (const key of keys) {
    try {
      const rows = await fetchEdgeBoard(sport, key);
      if (rows.length > 0) return rows;
    } catch {
      // try next key
    }
  }
  return [];
}

function withFallback(
  sport: string,
  oddsRows: EdgeBoardRow[],
): EdgeBoardRow[] {
  if (countPriced(oddsRows) > 0 || oddsRows.length > 0) return oddsRows;
  return loadEdgeBoardFallback(sport);
}

async function assembleNflEdgeBoardRows(
  oddsRows: EdgeBoardRow[],
  options?: AssembleEdgeBoardOptions,
): Promise<EdgeBoardRow[]> {
  const slate = options?.slate ?? "live";

  // Parallelize Odds + fair-lines so a slow Odds API cannot stack on Railway.
  const [pulledOdds, fair] = await Promise.all([
    pullOddsRows("nfl"),
    // Fair-lines pull also persists Odds API events into odds_snapshots for training.
    fetchNflFairLines({
      season: NFL_EDGE_BOARD_SEASON,
      daysAhead: 200,
      includePastDays: 14,
      bookmakers: ALLOWED_BOOKS.join(","),
    }),
  ]);
  const odds =
    countPriced(pulledOdds) >= countPriced(oddsRows) ? pulledOdds : oddsRows;

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
    return filterNflOddsPostedRows(rows);
  }

  rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
  rows = sortNflEdgeBoardRows(rows);

  if (slate === "live") {
    return filterNflCurrentWeekRows(rows, currentWeek);
  }
  // Full season tab: everything we currently have sportsbook odds on.
  return filterNflOddsPostedRows(rows);
}

/**
 * Pull live Odds (or fallback snapshot) and assemble KEI merge for any sport.
 * Preferred path for SSR pages — avoids serverless self-HTTP to /api/edge-board.
 */
export async function loadAssembledEdgeBoardRows(
  sportKey: string,
  options?: AssembleEdgeBoardOptions,
): Promise<EdgeBoardRow[]> {
  const sport = sportKey.toLowerCase();
  if (sport === "nfl") {
    return assembleEdgeBoardRows("nfl", [], options);
  }

  const pulled = await pullOddsRows(sport);
  const odds = withFallback(sport, pulled);
  return assembleEdgeBoardRows(sport, odds, options);
}

export async function assembleEdgeBoardRows(
  sportKey: string,
  oddsRows: EdgeBoardRow[],
  options?: AssembleEdgeBoardOptions,
): Promise<EdgeBoardRow[]> {
  const sport = sportKey.toLowerCase();
  if (sport === "nfl") {
    return assembleNflEdgeBoardRows(oddsRows, options);
  }

  const odds = withFallback(sport, oddsRows);
  const keiGames = await resolveKeiGames(sport);
  const seeded = ensureAllKeiGamesOnBoard(odds, sport, keiGames);
  return mergeKeiIntoEdgeBoardRows(seeded, sport, keiGames);
}
