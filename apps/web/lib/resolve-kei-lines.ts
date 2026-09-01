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
 * - NFL: real split when blend applied — model_* = pre-market-blend MC fair;
 *   handicap_* = published post-blend (+ totals cal). ML/win = identity (no pre-blend ML).
 *   Missing model_* → identity via applyHandicapIdentity. Never invent stub deltas.
 * - NBA / WNBA: published fair lines → handicap; model_* identity until API exposes split.
 * - NCAAM: kei_lines_ncaam.json → handicap (identity).
 * - CFB: kei_lines_cfb.json — handicap = published KEI; model_* = research fair.
 * - NHL: **markets-only** — resolveKeiGames returns [].
 */

import "server-only";

import { applyHandicapIdentity, type KeiLineGame } from "@/lib/kei-lines";
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
 * Handicap (KEI) = published spread_home / total_mean (post-blend product).
 * Model = pre-blend research when API provides modelSpreadHome / modelTotal;
 * otherwise leave unset → applyHandicapIdentity (identity). Edge Board tags
 * use handicap only.
 */
export function keiGamesFromNflFairLines(
  lines: NflFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    const handicapSpread = line.handicapSpreadHome ?? line.spreadHome;
    const handicapTotal = line.handicapTotal ?? line.totalMean;
    const handicapHomeMl = line.handicapHomeMl ?? line.fairHomeMl;
    const handicapAwayMl = line.handicapAwayMl ?? line.fairAwayMl;
    const handicapWin = line.handicapHomeWinProb ?? line.homeWinProb;

    // Only pass model_* when the API explicitly provided them (typed fields).
    // normalizeFairLine identity-fills model from handicap when API omits them;
    // that still means Model === KEI, which applyHandicapIdentity also yields.
    const modelSpread = line.modelSpreadHome ?? undefined;
    const modelTotal = line.modelTotal ?? undefined;

    return applyHandicapIdentity({
      id: line.gameId,
      homeTeam: line.homeTeam,
      awayTeam: line.awayTeam,
      homeAbbr: line.homeAbbr,
      awayAbbr: line.awayAbbr,
      commenceTime:
        // Single kickoff source shared with Edge Board / Weekly Slate.
        line.startTime ?? line.gameDate ?? undefined,
      handicapSpreadHome: handicapSpread,
      handicapTotal,
      handicapHomeMl,
      handicapAwayMl,
      handicapHomeWinProb: handicapWin,
      projSpreadHome: handicapSpread,
      projTotal: handicapTotal,
      projHomeMl: handicapHomeMl,
      projAwayMl: handicapAwayMl,
      homeWinProb: handicapWin,
      modelSpreadHome: modelSpread,
      modelTotal,
      modelHomeMl: line.modelHomeMl ?? undefined,
      modelAwayMl: line.modelAwayMl ?? undefined,
      modelHomeWinProb: line.modelHomeWinProb ?? undefined,
    });
  });
}

export async function resolveKeiGames(
  sportKey: string,
): Promise<KeiLineGame[]> {
  const sport = sportKey.toLowerCase();

  // Markets-only: NHL has no KEI source yet.
  if (sport === "nhl") {
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
      const board = await fetchNbaFairLines({
        daysAhead: 14,
        source: "auto",
      });
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
