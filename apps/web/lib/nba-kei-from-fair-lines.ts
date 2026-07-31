/**
 * Map NBA model-service fair-lines into KEI games for board merge / Fair Lines.
 */

import type { KeiLineGame } from "@/lib/kei-lines";
import type { NbaFairLineRow } from "@/lib/nba-fair-lines-format";

export function keiGamesFromNbaFairLines(
  lines: NbaFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => ({
    id: line.gameId,
    homeTeam: line.homeTeam,
    awayTeam: line.awayTeam,
    commenceTime: line.startTime ?? line.gameDate ?? undefined,
    projSpreadHome: line.fairSpreadHome,
    projTotal: line.fairTotal ?? line.totalMean,
  }));
}
