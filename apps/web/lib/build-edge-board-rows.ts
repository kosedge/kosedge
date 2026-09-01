/**
 * Shared edge-board assembly.
 * NFL: pulls REG fair-lines + Odds API overlay (projection-backed; no PRE odds-only).
 * Week 1 tab = every REG Week 1 schedule-pack game (schedule-driven; no silent drop).
 * Missing KEI / odds still appear with honest empties.
 * Full slate = projection-backed REG games in the pull window (+ complete Week 1).
 * Legacy aliases: `live` → week1, `all` → full.
 * KEI = published fair line (identity — no fake Model vs KEI split).
 * MLB: seeds from model-service fair-lines when Odds is empty (real model vs KEI).
 * NBA/WNBA: fair-lines → KEI handicap (model_* identity until pre_blend exists).
 * NCAAM: Odds + kei_lines_ncaam.json.
 * NHL: **markets-only** until a KEI model ships — Odds/fallback only;
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
  filterNflOddsPostedRows,
  filterNflProjectionBackedRows,
  filterNflStrictWeekRows,
  overlayOddsOntoFairLineRows,
  sortNflEdgeBoardRows,
  syncEdgeBoardActionsWithCurrent,
} from "@/lib/nfl-edge-board-from-fair-lines";
import {
  ensureNflScheduleWeekOnBoard,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { enrichNflEdgeBoardMatchupFields } from "@/lib/edge-board-matchup-enrich";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { applyCfbTrustedMarketToRows } from "@/lib/cfb-trusted-market";
import {
  applyNbaTrustedMarketToRows,
  isNbaPreseason,
} from "@/lib/nba-trusted-market";
import { applyWnbaTrustedMarketToRows } from "@/lib/wnba-trusted-market";
import { getKeiLines, type KeiLineGame } from "@/lib/kei-lines";
import {
  keiGamesFromNflFairLines,
  resolveKeiGames,
} from "@/lib/resolve-kei-lines";
import { getNflPowerRatingsBoard } from "@/lib/power-ratings";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";

const NFL_EDGE_BOARD_SEASON = 2026;

/** NFL Edge Board slate tabs. `live`/`all` kept as aliases. */
export type NflEdgeBoardSlate = "week1" | "full" | "live" | "all";

export type AssembleEdgeBoardOptions = {
  /** NFL: `week1` (default) = Week 1 REG only; `full` = multi-week projection slate. */
  slate?: NflEdgeBoardSlate;
};

export function normalizeNflEdgeBoardSlate(
  raw: string | null | undefined,
): "week1" | "full" {
  const v = String(raw ?? "")
    .trim()
    .toLowerCase();
  if (v === "full" || v === "all") return "full";
  // week1 | live | missing → Week 1 launch tab
  return "week1";
}

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

function withFallback(sport: string, oddsRows: EdgeBoardRow[]): EdgeBoardRow[] {
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
  const slate = normalizeNflEdgeBoardSlate(options?.slate);

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

  if (fair.lines.length > 0) {
    keiGames = keiGamesFromNflFairLines(fair.lines);
    rows = fairLinesToEdgeBoardRows(fair.lines);
    rows = overlayOddsOntoFairLineRows(rows, odds);
    // Odds/Current may arrive after fair-lines decision graded Mkt —; sync Action.
    rows = syncEdgeBoardActionsWithCurrent(rows);
  } else {
    // File KEI fallback — still projection-backed; never surface PRE odds-only.
    keiGames = getKeiLines("nfl");
    if (keiGames.length === 0) return [];
    rows = ensureAllKeiGamesOnBoard(odds, "nfl", keiGames);
    rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
    rows = filterNflProjectionBackedRows(rows);
    // Stamp REG week from schedule pack BEFORE Week 1 filter (root-cause fix).
    rows = stampNflEdgeBoardWeeksFromSchedule(rows);
    // Schedule is the driver: pad any REG Week 1 game missing after KEI filter.
    rows = ensureNflScheduleWeekOnBoard(rows, 1);
    rows = sortNflEdgeBoardRows(rows);
    if (slate === "week1") {
      return withMatchupEnrichment(filterNflStrictWeekRows(rows, 1));
    }
    // Full slate without fair-lines: priced projection rows when books exist,
    // plus schedule-complete Week 1 (empties allowed).
    const priced = filterNflOddsPostedRows(rows);
    return withMatchupEnrichment(ensureNflScheduleWeekOnBoard(priced, 1));
  }

  rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
  rows = filterNflProjectionBackedRows(rows);
  // Stamp missing week from 2026 schedule pack before any week filter.
  rows = stampNflEdgeBoardWeeksFromSchedule(rows);
  // Schedule-driven Week 1 membership (no silent drop when KEI/odds missing).
  rows = ensureNflScheduleWeekOnBoard(rows, 1);
  rows = sortNflEdgeBoardRows(rows);

  if (slate === "week1") {
    // Strict Week 1 REG — count must match schedule pack (normally 16).
    return withMatchupEnrichment(filterNflStrictWeekRows(rows, 1));
  }
  // Full slate: every projection-backed REG game in the pull window (+ complete W1).
  return withMatchupEnrichment(rows);
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
  const merged = mergeKeiIntoEdgeBoardRows(seeded, sport, keiGames);
  if (sport === "cfb") return applyCfbTrustedMarketToRows(merged);
  if (sport === "nba") {
    return applyNbaTrustedMarketToRows(merged, {
      preseason: isNbaPreseason(),
    });
  }
  if (sport === "wnba") {
    return applyWnbaTrustedMarketToRows(merged);
  }
  return merged;
}
