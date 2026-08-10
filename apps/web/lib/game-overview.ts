/**
 * Re-export Edge Board overview builder (canonical path: edge-board-matchup-overview).
 * Kept so older imports of `@/lib/game-overview` stay valid.
 */

export { generateGameOverview } from "@/lib/sports";
export {
  buildMatchupOverview,
  buildMatchupOverviewBlocks,
  assignDeskVoice,
  resolveSeasonPhase,
  isNeutralSite,
} from "@/lib/edge-board-matchup-overview";
