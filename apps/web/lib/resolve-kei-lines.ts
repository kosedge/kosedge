/**
 * Resolve KEI games for a sport. NFL prefers live Kosedge fair-lines
 * (spread_home / total_mean); MLB/NBA prefer model-service fair-lines;
 * others fall back to kei_lines_{sport}.json.
 *
 * Unified shape: handicap_* = KEI product line; model_* = pure sim when available.
 * Edgeboard always merges handicap (identity fallback).
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
 * Published blended spread/total → handicap (KEI).
 * TODO(model-honesty): when fair-lines API exposes pre_blend_* / raw model,
 * map those to model_*; until then model_* = handicap (identity) and UI says KEI.
 */
export function keiGamesFromNflFairLines(
  lines: NflFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    // Prefer explicit model fields when API grows them (stubs today).
    const raw = line as NflFairLineRow & {
      modelSpreadHome?: number | null;
      modelTotal?: number | null;
      preBlendSpreadHome?: number | null;
      preBlendTotal?: number | null;
    };
    const handicapSpread = line.spreadHome;
    const handicapTotal = line.totalMean;
    const modelSpread =
      raw.modelSpreadHome ?? raw.preBlendSpreadHome ?? handicapSpread;
    const modelTotal =
      raw.modelTotal ?? raw.preBlendTotal ?? handicapTotal;

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
      modelSpreadHome: modelSpread,
      modelTotal,
    });
  });
}

export async function resolveKeiGames(
  sportKey: string,
): Promise<KeiLineGame[]> {
  const sport = sportKey.toLowerCase();

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
