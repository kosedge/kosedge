/**
 * Map NHL model-service fair-lines into KEI games for board merge.
 *
 * Published fair_* → handicap (KEI). model_* identity until pre_blend exists.
 */

import { applyHandicapIdentity, type KeiLineGame } from "@/lib/kei-lines";
import type { NhlFairLineRow } from "@/lib/nhl-fair-lines-format";

export function keiGamesFromNhlFairLines(
  lines: NhlFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    const handicapSpread = line.fairSpreadHome;
    const handicapTotal = line.fairTotal ?? line.totalMean;

    return applyHandicapIdentity({
      id: line.gameId,
      homeTeam: line.homeTeam,
      awayTeam: line.awayTeam,
      homeAbbr: line.homeAbbr,
      awayAbbr: line.awayAbbr,
      commenceTime: line.startTime ?? line.gameDate ?? undefined,
      handicapSpreadHome: handicapSpread,
      handicapTotal,
      handicapHomeWinProb: line.homeWinProb,
      projSpreadHome: handicapSpread,
      projTotal: handicapTotal,
      homeWinProb: line.homeWinProb,
      modelSpreadHome: handicapSpread,
      modelTotal: handicapTotal,
      modelHomeWinProb: line.homeWinProb,
    });
  });
}
