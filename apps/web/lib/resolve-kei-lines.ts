/**
 * Resolve KEI games for a sport. NFL prefers live Kosedge fair-lines
 * (spread_home / total_mean); MLB/NBA/WNBA prefer model-service fair-lines;
 * others fall back to kei_lines_{sport}.json.
 *
 * Unified shape: handicap_* = KEI product line; model_* = pure sim when available.
 * Edgeboard always merges handicap (identity fallback via applyHandicapIdentity).
 *
 * Model vs KEI honesty (2026-08):
 * - MLB: real split — model_* = first daily PA sim snapshot; handicap_* = nowcast re-sim.
 * - NFL / NBA / WNBA: published fair lines map to handicap (KEI). model_* is identity
 *   until fair-lines APIs expose pre_blend_* / raw model. Do not invent a fake split.
 * - NCAAM: kei_lines_ncaam.json → handicap (identity).
 * - NHL / CFB: **markets-only** — no fair-lines / kei_lines source yet. resolveKeiGames
 *   returns []. UI must not invent KEI or show “Coming soon”; see sportIsMarketsOnlyEdgeBoard.
 */

import "server-only";

import {
  applyHandicapIdentity,
  type KeiLineGame,
} from "@/lib/kei-lines";
import { getKeiLines } from "@/lib/kei-lines";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { keiGamesFromMlbFairLines } from "@/lib/mlb-kei-from-fair-lines";
import { fetchNbaFairLines } from "@/lib/nba-fair-lines";
import { keiGamesFromNbaFairLines } from "@/lib/nba-kei-from-fair-lines";
import { fetchNflFairLines, type NflFairLineRow } from "@/lib/nfl-fair-lines";
import { fetchWnbaFairLines } from "@/lib/wnba-fair-lines";
import { keiGamesFromWnbaFairLines } from "@/lib/wnba-kei-from-fair-lines";

const NFL_KEI_SEASON = 2026;

/**
 * Map NFL fair-lines → KEI games.
 * Published fair line (spread_home / total_mean) → handicap (KEI).
 * Honesty contract: no Model vs KEI split yet — leave model_* unset so
 * applyHandicapIdentity copies handicap → model (identity). Do not invent
 * a pure-model layer from untyped stubs.
 */
export function keiGamesFromNflFairLines(
  lines: NflFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    const handicapSpread = line.spreadHome;
    const handicapTotal = line.totalMean;

    return applyHandicapIdentity({
      id: line.gameId,
      homeTeam: line.homeTeam,
      awayTeam: line.awayTeam,
      homeAbbr: line.homeAbbr,
      awayAbbr: line.awayAbbr,
      commenceTime: line.startTime ?? line.gameDate ?? undefined,
      handicapSpreadHome: handicapSpread,
      handicapTotal,
      projSpreadHome: handicapSpread,
      projTotal: handicapTotal,
    });
  });
}

export async function resolveKeiGames(
  sportKey: string,
): Promise<KeiLineGame[]> {
  const sport = sportKey.toLowerCase();

  // Markets-only sports: no KEI source yet (NHL / CFB). Empty → EdgeBoard
  // shows Open/Best only; never fabricate handicap lines.
  if (sport === "nhl" || sport === "cfb") {
    return [];
  }

  if (sport === "nfl") {
    try {
      const board = await fetchNflFairLines({
        season: NFL_KEI_SEASON,
        daysAhead: 120,
        includePastDays: 7,
      });
      if (board.lines.length > 0) {
        return keiGamesFromNflFairLines(board.lines);
      }
    } catch {
      // fall through to file export
    }
  }

  if (sport === "mlb") {
    try {
      const board = await fetchMlbFairLines();
      if (board.lines.length > 0) {
        return keiGamesFromMlbFairLines(board.lines);
      }
    } catch {
      // fall through to file export
    }
  }

  if (sport === "nba") {
    try {
      const board = await fetchNbaFairLines({ daysAhead: 5 });
      if (board.lines.length > 0) {
        return keiGamesFromNbaFairLines(board.lines);
      }
    } catch {
      // fall through to file export
    }
  }

  if (sport === "wnba") {
    try {
      const board = await fetchWnbaFairLines({ daysAhead: 5 });
      if (board.lines.length > 0) {
        return keiGamesFromWnbaFairLines(board.lines);
      }
    } catch {
      // fall through to file export
    }
  }

  return getKeiLines(sport);
}
