/**
 * Map WNBA model-service fair-lines into KEI games for board merge / Fair Lines.
 */

import type { KeiLineGame } from "@/lib/kei-lines";
import type { WnbaFairLineRow } from "@/lib/wnba-fair-lines-format";

export function keiGamesFromWnbaFairLines(
  lines: WnbaFairLineRow[],
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
