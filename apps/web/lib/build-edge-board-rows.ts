/**
 * Shared edge-board assembly.
 * NFL: pulls REG fair-lines + Odds API overlay (projection-backed; no PRE odds-only).
 * Live = current REG week; Odds slate = projection-backed games with books.
 * KEI = published fair line (identity — no fake Model vs KEI split).
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
  filterNflProjectionBackedRows,
  overlayOddsOntoFairLineRows,
  sortNflEdgeBoardRows,
} from "@/lib/nfl-edge-board-from-fair-lines";
import { enrichNflEdgeBoardMatchupFields } from "@/lib/edge-board-matchup-enrich";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { getKeiLines, type KeiLineGame } from "@/lib/kei-lines";
import {
  keiGamesFromNflFairLines,
  resolveKeiGames,
} from "@/lib/resolve-kei-lines";
import { getNflPowerRatingsBoard } from "@/lib/power-ratings";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";

const NFL_EDGE_BOARD_SEASON = 2026;

export type AssembleEdgeBoardOptions = {
  /** NFL: `live` = current REG week; `all` = projection-backed games with books. */
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

function nflLaunchPowerByAbbr(): Map<string, number> {
  const map = new Map<string, number>();
  try {
    const board = getNflPowerRatingsBoard();
    for (const row of board.rows) {
      const abbr = canonicalizeNflTeam(row.teamNorm || row.team);
      if (!abbr || !Number.isFinite(row.rating)) continue;
      map.set(abbr, row.rating);
      if (abbr === "LAR" || abbr === "LA") {
        map.set("LAR", row.rating);
        map.set("LA", row.rating);
      }
    }
  } catch {
    // Power optional — KEI proxy still fills Stat Drop.
  }
  return map;
}

function withMatchupEnrichment(rows: EdgeBoardRow[]): EdgeBoardRow[] {
  return enrichNflEdgeBoardMatchupFields(rows, {
    powerByAbbr: nflLaunchPowerByAbbr(),
  });
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
    // File KEI fallback — still projection-backed; never surface PRE odds-only.
    keiGames = getKeiLines("nfl");
    if (keiGames.length === 0) return [];
    rows = ensureAllKeiGamesOnBoard(odds, "nfl", keiGames);
    rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
    rows = filterNflProjectionBackedRows(rows);
    rows = sortNflEdgeBoardRows(rows);
    // Without fair-lines currentWeek, priced projection slate only (honest).
    return withMatchupEnrichment(filterNflOddsPostedRows(rows));
  }

  rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
  rows = filterNflProjectionBackedRows(rows);
  rows = sortNflEdgeBoardRows(rows);

  if (slate === "live") {
    let live = filterNflCurrentWeekRows(rows, currentWeek);
    const anyWeek = live.some((r) =>
      Number.isFinite(Number((r as { week?: number }).week)),
    );
    // When week is absent on every row, stamp currentWeek then keep a live
    // window by commence time so we don't dump the full season as "Week 1".
    if (!anyWeek && live.length > 0) {
      const now = Date.now();
      const horizonMs = 10 * 24 * 60 * 60 * 1000;
      const dated = live.filter((r) => {
        const t = Date.parse(String(r.commenceTime ?? ""));
        return Number.isFinite(t) && t >= now - 2 * 24 * 60 * 60 * 1000 && t <= now + horizonMs;
      });
      live = dated.length > 0 ? dated : live.slice(0, 40);
      for (const r of live) {
        (r as EdgeBoardRow & { week?: number }).week = currentWeek;
      }
    }
    const stampedWeek =
      live
        .map((r) => Number((r as { week?: number }).week))
        .find((w) => Number.isFinite(w)) ?? currentWeek;
    for (const r of live) {
      const row = r as EdgeBoardRow & {
        week?: number;
        gamesPlayedAway?: number;
        gamesPlayedHome?: number;
      };
      if (row.week == null || !Number.isFinite(Number(row.week))) {
        row.week = stampedWeek;
      }
      if (Number(row.week) === 1) {
        if (row.gamesPlayedAway == null) row.gamesPlayedAway = 0;
        if (row.gamesPlayedHome == null) row.gamesPlayedHome = 0;
      }
    }
    return withMatchupEnrichment(live);
  }
  // Odds slate: projection-backed games that currently have sportsbook prices.
  return withMatchupEnrichment(filterNflOddsPostedRows(rows));
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
