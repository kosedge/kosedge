/**
 * Shared edge-board assembly.
 * NFL: pulls REG fair-lines + Odds API overlay. REG odds-without-KEI stay
 * (honest blank Fair). PRE exhibitions stay off. Week 1 schedule games are
 * always present; posted future markets append with horizon labels.
 * Full slate = governed snapshot only (INC-2026-09-07) — never live daysAhead=200.
 * Week 1 / live uses narrow fair-lines window.
 * Legacy aliases: `live` → week1, `all` → full.
 * KEI = published fair line (identity — no fake Model vs KEI split).
 * MLB: seeds from model-service fair-lines when Odds is empty (real model vs KEI).
 * NBA/WNBA/NHL: fair-lines → KEI handicap (model_* identity until pre_blend exists).
 * NCAAM: Odds + kei_lines_ncaam.json.
 * Never invents sportsbook or KEI prices; empty offseason boards stay empty honestly.
 */

import type { EdgeBoardRow } from "@kosedge/contracts";
import {
  ensureAllKeiGamesOnBoard,
  mergeKeiIntoEdgeBoardRows,
} from "@/lib/edge-board-kei";
import { loadEdgeBoardFallback } from "@/lib/edge-board-fallback";
import { applyTotalIdentityGateToRows } from "@/lib/edge-board-total-identity-gate";
import { getOddsApiKeys } from "@/lib/odds-api-keys";
import { ALLOWED_BOOKS, fetchEdgeBoard } from "@/lib/odds-api";
import {
  fairLinesToEdgeBoardRows,
  filterNflProjectionBackedRows,
  overlayOddsOntoFairLineRows,
  resolveEdgeBoardLinesAsOf,
  syncEdgeBoardActionsWithCurrent,
} from "@/lib/nfl-edge-board-from-fair-lines";
import {
  ensureNflScheduleWeekOnBoard,
  stampNflEdgeBoardWeeksFromSchedule,
} from "@/lib/nfl-edge-board-week";
import { nflAssembleWindowForSlate } from "@/lib/nfl-edge-board-assemble-window";
import { enrichNflEdgeBoardMatchupFields } from "@/lib/edge-board-matchup-enrich";
import { fetchNflFairLines } from "@/lib/nfl-fair-lines";
import { applyCfbTrustedMarketToRows } from "@/lib/cfb-trusted-market";
import { loadCfbCurrentMarketRows } from "@/lib/cfb-edge-board-odds";
import {
  applyNbaTrustedMarketToRows,
  isNbaPreseason,
} from "@/lib/nba-trusted-market";
import {
  applyNhlTrustedMarketToRows,
  isNhlPreseason,
} from "@/lib/nhl-trusted-market";
import { applyWnbaTrustedMarketToRows } from "@/lib/wnba-trusted-market";
import { getKeiLines, type KeiLineGame } from "@/lib/kei-lines";
import {
  keiGamesFromNflFairLines,
  resolveKeiGames,
} from "@/lib/resolve-kei-lines";
import { getNflPowerRatingsBoard } from "@/lib/power-ratings";
import { canonicalizeNflTeam } from "@/lib/nfl-canonical-teams";
import { applyOddsHorizonToRows } from "@/lib/odds-horizon";

const NFL_EDGE_BOARD_SEASON = 2026;

/** Backfill sanitized payload odds_as_of onto rows missing linesAsOf. */
function applyPayloadOddsAsOfToRows(
  rows: EdgeBoardRow[],
  payloadOddsAsOf: string | null,
): EdgeBoardRow[] {
  const stamp = resolveEdgeBoardLinesAsOf({
    oddsCapturedAt: null,
    oddsAsOf: payloadOddsAsOf,
  });
  if (!stamp) return rows;
  for (const r of rows) {
    const row = r as EdgeBoardRow & { linesAsOf?: string };
    if (!row.linesAsOf) row.linesAsOf = stamp;
  }
  return rows;
}

/** NFL Edge Board slate tabs. `live`/`all` kept as aliases. */
export type NflEdgeBoardSlate = "week1" | "full" | "live" | "all";

export type AssembleEdgeBoardOptions = {
  /** NFL: `week1` (default) = Week 1 REG only; `full` = multi-week projection slate. */
  slate?: NflEdgeBoardSlate;
  /** Fair-lines upstream abort (page-data assemble uses pageData budget). */
  timeoutMs?: number;
  /**
   * Page-data assemble: throw on fair-lines transport failure instead of
   * soft-falling to a KEI file pack without market vintage.
   */
  throwOnTransportError?: boolean;
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
  // INC-2026-09-07 (C): customer full slate is governed snapshot only — never
  // live-pull fair-lines with daysAhead=200 on this path.
  if (slate === "full") {
    throw new Error(
      "NFL full-slate assemble unavailable: refusing live daysAhead=200 path; " +
        "governed cache/snapshot required (INC-2026-09-07).",
    );
  }
  // Week 1 / live uses narrow customer window.
  const window = nflAssembleWindowForSlate("week1");

  // WS-02 DUP-C / S2: single Odds acquire then fair-lines reuse — never live∥live.
  // D1: pullOddsRows once; fair-lines oddsMode=reuse skips model fetch_odds.
  const pulledOdds = await pullOddsRows("nfl");
  const odds =
    countPriced(pulledOdds) >= countPriced(oddsRows) ? pulledOdds : oddsRows;
  // Fair-lines page-data/SSR send persist=0 — odds_snapshots land via beat/worker only.
  const fair = await fetchNflFairLines({
    season: NFL_EDGE_BOARD_SEASON,
    daysAhead: window.daysAhead,
    includePastDays: window.includePastDays,
    bookmakers: ALLOWED_BOOKS.join(","),
    timeoutMs: options?.timeoutMs,
    throwOnTransportError: options?.throwOnTransportError,
    // reuse + oddsPayload → model skips fetch_odds; empty Odds → skip (still ≤1).
    ...(odds.length > 0
      ? { oddsMode: "reuse" as const, oddsPayload: odds }
      : { oddsMode: "skip" as const }),
  });

  let keiGames: KeiLineGame[] = [];
  let rows: EdgeBoardRow[] = [];
  /** Payload odds_as_of — same market vintage as fair-lines; never request clock. */
  const payloadOddsAsOf = fair.oddsAsOf ?? null;

  if (fair.lines.length > 0) {
    keiGames = keiGamesFromNflFairLines(fair.lines);
    rows = fairLinesToEdgeBoardRows(fair.lines, {
      // Same market vintage as fair-lines (payload odds_as_of).
      // Never fair.asOf / board generation / request clock.
      oddsAsOf: payloadOddsAsOf,
    });
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
    rows = stampNflEdgeBoardWeeksFromSchedule(rows);
    rows = ensureNflScheduleWeekOnBoard(rows, 1);
    rows = applyOddsHorizonToRows(rows);
    return withMatchupEnrichment(rows);
  }

  rows = mergeKeiIntoEdgeBoardRows(rows, "nfl", keiGames);
  rows = filterNflProjectionBackedRows(rows);
  rows = stampNflEdgeBoardWeeksFromSchedule(rows);
  rows = ensureNflScheduleWeekOnBoard(rows, 1);
  rows = applyPayloadOddsAsOfToRows(rows, payloadOddsAsOf);
  rows = applyOddsHorizonToRows(rows);
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

  if (sport === "cfb") {
    const market = await loadCfbCurrentMarketRows({
      timeoutMs: options?.timeoutMs,
    });
    return assembleEdgeBoardRows("cfb", market.rows, options);
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
  let rows: EdgeBoardRow[];
  if (sport === "nfl") {
    rows = await assembleNflEdgeBoardRows(oddsRows, options);
  } else {
    // CFB: caller already applied current-market freshness. Do not hydrate
    // the July 31 NFT snapshot as live MARKET.
    const odds = sport === "cfb" ? oddsRows : withFallback(sport, oddsRows);
    const keiGames = await resolveKeiGames(sport);
    const seeded = ensureAllKeiGamesOnBoard(odds, sport, keiGames);
    const merged = mergeKeiIntoEdgeBoardRows(seeded, sport, keiGames);
    if (sport === "cfb") {
      rows = applyCfbTrustedMarketToRows(merged);
    } else if (sport === "nba") {
      rows = applyNbaTrustedMarketToRows(merged, {
        preseason: isNbaPreseason(),
      });
    } else if (sport === "wnba") {
      rows = applyWnbaTrustedMarketToRows(merged);
    } else if (sport === "nhl") {
      rows = applyNhlTrustedMarketToRows(merged, {
        preseason: isNhlPreseason(),
      });
    } else {
      rows = merged;
    }
  }
  // INC-2026-09-10: totals without period identity / in-play quotes fail closed.
  rows = applyTotalIdentityGateToRows(rows, sport);
  return applyOddsHorizonToRows(rows);
}
