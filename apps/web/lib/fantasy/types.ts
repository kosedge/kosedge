/**
 * Fantasy Draft Desk shared types.
 * Built on season-engine / projection-baseline outputs — not a separate model.
 */

import type { AdpQaFlag } from "@/lib/fantasy/adp-qa-flags";

export type FantasyScoringProfile = "standard" | "half_ppr" | "ppr";

export type FantasyDraftPosition = "QB" | "RB" | "WR" | "TE" | "K" | "DST";

export type ScheduleWindowNote = {
  early: "soft" | "neutral" | "hard";
  playoff: "soft" | "neutral" | "hard";
  label: string;
  detail: string;
};

export type RiskFlag = {
  kind: "committee" | "availability" | "depth_volatility" | "rookie";
  label: string;
  detail: string;
};

export type FantasyDeskRow = {
  season: number;
  scoringProfile: FantasyScoringProfile;
  modelVersion: string;
  playerId: string;
  playerUid: string | null;
  playerName: string;
  team: string;
  position: string;
  gamesProjected: number;
  passYardsTotal: number;
  rushYardsTotal: number;
  receivingYardsTotal: number;
  receptionsTotal: number;
  passTdsTotal: number;
  rushTdsTotal: number;
  recTdsTotal: number;
  totalPoints: number;
  floorPoints: number;
  medianPoints: number;
  ceilingPoints: number;
  replacementPoints: number;
  valueOverReplacement: number;
  rankOverall: number;
  /**
   * Board display order after value-aware desk policy (1 = first row).
   * Distinct from `rankOverall` (raw model VOR rank). Absent on rows that
   * have not been through `applyDeskRankPolicy`.
   */
  deskOrder?: number;
  rankPosition: number;
  tier: string;
  /**
   * Market ADP (FantasyPros consensus average). Null when unmatched / feed missing —
   * never invent precision.
   */
  adp: number | null;
  /** ADP − modelRank: positive = value (model likes more than market), negative = reach. */
  valueDelta: number | null;
  /** FantasyPros display name when ADP matched. */
  adpMatchedName: string | null;
  /** high = same-format ADP (Value Δ allowed); cross_format = sibling panel ADP only. */
  adpMatchConfidence: "high" | "cross_format" | null;
  isRookie: boolean;
  rookieYear: number | null;
  draftNumber: number | null;
  schedule: ScheduleWindowNote;
  riskFlags: RiskFlag[];
  expertBlurb: string;
  drivers: string[];
  /**
   * High |modelRank − ADP| QA stamp. Null when unmatched ADP or gap is
   * inside the position threshold — never a silent wall of outliers.
   */
  adpQaFlag?: AdpQaFlag | null;
  updatedAt: string | null;
  source: "model-service" | "preseason-fallback";
};

export type FantasyDeskBoard = {
  season: number;
  scoringProfile: FantasyScoringProfile;
  count: number;
  rows: FantasyDeskRow[];
  source: "model-service" | "preseason-fallback" | "empty";
  adpSourceLabel: string;
  adpFreshnessLabel: string;
  adpOrigin: "live" | "snapshot" | "none";
  adpMatchedCount: number;
  adpMatchedHighCount: number;
  adpMatchedCrossFormatCount: number;
  adpUnmatched: Array<{
    playerId: string;
    playerName: string;
    team: string;
    position: string;
    rankOverall: number | null;
  }>;
  limitations: string[];
  error?: string;
  slateStatus?: string;
};

export type RosterSlot =
  | "QB"
  | "RB1"
  | "RB2"
  | "WR1"
  | "WR2"
  | "TE"
  | "FLEX"
  | "K"
  | "DST"
  | "BENCH";

export type TeamBuilderRoster = {
  slots: Partial<Record<RosterSlot, string | null>>;
  playerIds: string[];
};
