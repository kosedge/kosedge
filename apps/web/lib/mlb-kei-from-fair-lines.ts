/**
 * Map MLB model-service fair-lines into KEI games for board merge / Fair Lines.
 *
 * Handicap (KEI) → proj* / homeWinProb / handicap*
 * Model (pure sim) → model* (Fair Lines desk; not used for edge tags)
 *
 * KEI total is the certified nearest-half-run fair total (`resolveMlbKeiTotal`),
 * not the raw `totalMean`. 9.09 → 9.0 is policy, not a stub constant.
 */

import { applyHandicapIdentity, type KeiLineGame } from "@/lib/kei-lines";
import type { MlbFairLineRow } from "@/lib/mlb-fair-lines-format";
import { resolveMlbKeiTotal } from "@/lib/mlb-fair-total";

export function keiGamesFromMlbFairLines(
  lines: MlbFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    const handicapSpread =
      line.handicapSpreadHome ?? line.fairSpreadHome ?? null;
    const handicapTotal = resolveMlbKeiTotal(line).kei;
    const handicapHomeMl = line.handicapHomeMl ?? line.fairHomeMl ?? null;
    const handicapAwayMl = line.handicapAwayMl ?? line.fairAwayMl ?? null;
    const handicapWin = line.handicapHomeWinProb ?? line.homeWinProb ?? null;

    const modelSpread = line.modelSpreadHome ?? handicapSpread;
    const modelTotal = line.modelTotal ?? line.modelTotalMean ?? handicapTotal;
    const modelHomeMl = line.modelHomeMl ?? handicapHomeMl;
    const modelAwayMl = line.modelAwayMl ?? handicapAwayMl;
    const modelWin = line.modelHomeWinProb ?? handicapWin;

    return applyHandicapIdentity({
      id: line.gameId,
      homeTeam: line.homeTeam,
      awayTeam: line.awayTeam,
      commenceTime: line.startTime ?? line.gameDate ?? undefined,
      // T.period — fair_fg_* / handicap totals are full-game pregame.
      period: "fg",
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
