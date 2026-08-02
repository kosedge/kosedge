/**
 * Map MLB model-service fair-lines into KEI games for board merge / Fair Lines.
 *
 * Handicap (KEI) → proj* / homeWinProb / handicap*
 * Model (pure sim) → model* (Fair Lines desk; not used for edge tags)
 */

import {
  applyHandicapIdentity,
  type KeiLineGame,
} from "@/lib/kei-lines";
import type { MlbFairLineRow } from "@/lib/mlb-fair-lines-format";

export function keiGamesFromMlbFairLines(
  lines: MlbFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    const handicapSpread =
      line.handicapSpreadHome ?? line.fairSpreadHome ?? null;
    const handicapTotal =
      line.handicapTotal ?? line.fairTotal ?? line.totalMean ?? null;
    const handicapHomeMl = line.handicapHomeMl ?? line.fairHomeMl ?? null;
    const handicapAwayMl = line.handicapAwayMl ?? line.fairAwayMl ?? null;
    const handicapWin =
      line.handicapHomeWinProb ?? line.homeWinProb ?? null;

    const modelSpread =
      line.modelSpreadHome ?? handicapSpread;
    const modelTotal = line.modelTotal ?? line.modelTotalMean ?? handicapTotal;
    const modelHomeMl = line.modelHomeMl ?? handicapHomeMl;
    const modelAwayMl = line.modelAwayMl ?? handicapAwayMl;
    const modelWin = line.modelHomeWinProb ?? handicapWin;

    return applyHandicapIdentity({
      id: line.gameId,
      homeTeam: line.homeTeam,
      awayTeam: line.awayTeam,
      commenceTime: line.startTime ?? line.gameDate ?? undefined,
      // Handicap = KEI (edgeboard)
      handicapSpreadHome: handicapSpread,
      handicapTotal,
      handicapHomeMl,
      handicapAwayMl,
      handicapHomeWinProb: handicapWin,
      // Migration aliases
      projSpreadHome: handicapSpread,
      projTotal: handicapTotal,
      projHomeMl: handicapHomeMl,
      projAwayMl: handicapAwayMl,
      homeWinProb: handicapWin,
      // Model = research
      modelSpreadHome: modelSpread,
      modelTotal,
      modelHomeMl,
      modelAwayMl,
      modelHomeWinProb: modelWin,
    });
  });
}
