/**
 * Map WNBA model-service fair-lines into KEI games for board merge / Fair Lines.
 *
 * Published fair_* (may include market blend) → handicap (KEI).
 * Honesty: pure Model snapshot is NOT separated yet — model_* = handicap (identity).
 * When API exposes pre_blend_* / raw model, map those to model_*.
 */

import {
  applyHandicapIdentity,
  type KeiLineGame,
} from "@/lib/kei-lines";
import type { WnbaFairLineRow } from "@/lib/wnba-fair-lines-format";

export function keiGamesFromWnbaFairLines(
  lines: WnbaFairLineRow[],
): KeiLineGame[] {
  return lines.map((line) => {
    const raw = line as WnbaFairLineRow & {
      modelSpreadHome?: number | null;
      modelTotal?: number | null;
      preBlendSpreadHome?: number | null;
      preBlendTotal?: number | null;
    };
    const handicapSpread = line.fairSpreadHome;
    const handicapTotal = line.fairTotal ?? line.totalMean;
    const modelSpread =
      raw.modelSpreadHome ?? raw.preBlendSpreadHome ?? handicapSpread;
    const modelTotal =
      raw.modelTotal ?? raw.preBlendTotal ?? handicapTotal;

    return applyHandicapIdentity({
      id: line.gameId,
      homeTeam: line.homeTeam,
      awayTeam: line.awayTeam,
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
