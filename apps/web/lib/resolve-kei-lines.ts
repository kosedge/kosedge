/**
 * Resolve KEI games for a sport. NFL prefers live Kosedge fair-lines
 * (spread_home / total_mean); falls back to kei_lines_nfl.json.
 */

import "server-only";

import type { KeiLineGame } from "@/lib/kei-lines";
import { getKeiLines } from "@/lib/kei-lines";
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
  if (sportKey.toLowerCase() === "nfl") {
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
  return getKeiLines(sportKey);
}
