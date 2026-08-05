/**
 * Fantasy Draft Desk Phase 1 shared types.
 * Built on season-engine / projection-baseline outputs — not a separate model.
 */

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
  rankPosition: number;
  tier: string;
  /** Consensus-style ADP proxy (not a live FantasyPros/Sleeper feed). */
  adp: number;
  /** modelRank - adp: positive = value (model likes more than ADP), negative = reach. */
  valueDelta: number;
  isRookie: boolean;
  rookieYear: number | null;
  draftNumber: number | null;
  schedule: ScheduleWindowNote;
  riskFlags: RiskFlag[];
  expertBlurb: string;
  drivers: string[];
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
