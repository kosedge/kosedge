/**
 * Resolve KEI games for a sport. NFL prefers live Kosedge fair-lines
 * (spread_home / total_mean); MLB/NBA prefer model-service fair-lines;
 * others fall back to kei_lines_{sport}.json.
 */

import "server-only";

import type { KeiLineGame } from "@/lib/kei-lines";
import { getKeiLines } from "@/lib/kei-lines";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { keiGamesFromMlbFairLines } from "@/lib/mlb-kei-from-fair-lines";
import { fetchNbaFairLines } from "@/lib/nba-fair-lines";
import { keiGamesFromNbaFairLines } from "@/lib/nba-kei-from-fair-lines";
import { fetchNflFairLines, type NflFairLineRow } from "@/lib/nfl-fair-lines";

const NFL_KEI_SEASON = 2026;

export function keiGamesFromNflFairLines(
  lines: NflFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => ({
    id: line.gameId,
    homeTeam: line.homeTeam,
    awayTeam: line.awayTeam,
    homeAbbr: line.homeAbbr,
    awayAbbr: line.awayAbbr,
    commenceTime: line.startTime ?? line.gameDate ?? undefined,
    projSpreadHome: line.spreadHome,
    projTotal: line.totalMean,
  }));
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

  return getKeiLines(sport);
}
