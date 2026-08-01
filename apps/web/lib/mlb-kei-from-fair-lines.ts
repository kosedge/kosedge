/**
 * Map MLB model-service fair-lines into KEI games for board merge / Fair Lines.
 */

import type { KeiLineGame } from "@/lib/kei-lines";
import type { MlbFairLineRow } from "@/lib/mlb-fair-lines-format";

export function keiGamesFromMlbFairLines(
  lines: MlbFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => ({
    id: line.gameId,
    homeTeam: line.homeTeam,
    awayTeam: line.awayTeam,
    commenceTime: line.startTime ?? line.gameDate ?? undefined,
    // Keep run-line fair for desks that still consume projSpreadHome.
    projSpreadHome: line.fairSpreadHome,
    projTotal: line.fairTotal ?? line.totalMean,
    projHomeMl: line.fairHomeMl,
    projAwayMl: line.fairAwayMl,
    homeWinProb: line.homeWinProb,
  }));
}
