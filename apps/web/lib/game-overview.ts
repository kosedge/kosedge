/**
 * Edge Board overview — delegates to structured matchup engine.
 * Legacy generic pros/cons removed (sounded the same on every card).
 */

import { buildMatchupContext } from "@/lib/edge-board-matchup-context";
import { generateStructuredGameOverview } from "@/lib/edge-board-matchup-overview";

export function generateGameOverview(
  awayTeam: string,
  homeTeam: string,
  opts?: {
    gameId?: string;
    week?: number | null;
    awayAbbr?: string | null;
    homeAbbr?: string | null;
  },
): string {
  const ctx = buildMatchupContext({
    gameId: opts?.gameId ?? `${awayTeam}|${homeTeam}`,
    awayName: awayTeam,
    homeName: homeTeam,
    awayAbbr: opts?.awayAbbr,
    homeAbbr: opts?.homeAbbr,
    week: opts?.week ?? null,
  });
  return generateStructuredGameOverview(ctx);
}
