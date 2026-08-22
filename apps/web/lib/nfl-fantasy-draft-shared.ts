/**
 * Client-safe fantasy draft UI helpers + types.
 * Keep fetch / env access in `nfl-fantasy-draft.ts` (server-only).
 */

export type FantasyScoringProfile = "standard" | "half_ppr" | "ppr";

export const FANTASY_SCORING_PROFILES: Array<{
  value: FantasyScoringProfile;
  label: string;
}> = [
  { value: "ppr", label: "PPR" },
  { value: "half_ppr", label: "Half PPR" },
  { value: "standard", label: "Standard" },
];

export const FANTASY_DRAFT_POSITIONS = [
  "QB",
  "RB",
  "WR",
  "TE",
  "K",
  "DST",
] as const;
export type FantasyDraftPosition = (typeof FANTASY_DRAFT_POSITIONS)[number];

export type NflFantasyDraftRankingRow = {
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
  fieldGoalsMadeTotal: number | null;
  fieldGoalsAttemptedTotal: number | null;
  extraPointsMadeTotal: number | null;
  pointsAllowedTotal: number | null;
  sacksTotal: number | null;
  defInterceptionsTotal: number | null;
  fumbleRecoveriesTotal: number | null;
  defensiveTdsTotal: number | null;
  safetiesTotal: number | null;
  totalPoints: number;
  floorPoints: number | null;
  medianPoints: number | null;
  ceilingPoints: number | null;
  replacementPoints: number;
  valueOverReplacement: number;
  rankOverall: number;
  rankPosition: number;
  tier: string;
  isRookie: boolean;
  rookieYear: number | null;
  draftNumber: number | null;
  updatedAt: string | null;
};

export type NflFantasyDraftRankingsResponse = {
  count: number;
  rows: NflFantasyDraftRankingRow[];
  error?: string;
  slateStatus?: string;
};

export const DRAFT_TIER_LABELS: Record<string, string> = {
  elite: "Elite",
  QB1: "QB1",
  QB2: "QB2",
  RB1: "RB1",
  RB2: "RB2",
  WR1: "WR1",
  WR2: "WR2",
  TE1: "TE1",
  K1: "K1",
  DST1: "DST1",
  flex: "Flex",
  streamer: "Streamer",
  bench: "Bench",
  starter: "Starter",
};

export function draftTierLabel(tier: string): string {
  return DRAFT_TIER_LABELS[tier] ?? tier;
}

export function draftTierBadgeClass(tier: string): string {
  switch (tier) {
    case "elite":
      return "border-kos-gold/50 bg-kos-gold/15 text-kos-gold";
    case "QB1":
    case "RB1":
    case "WR1":
    case "TE1":
    case "K1":
    case "DST1":
    case "starter":
      return "border-edge-green/40 bg-edge-green/10 text-edge-green";
    case "QB2":
    case "RB2":
    case "WR2":
    case "flex":
      return "border-sky-400/40 bg-sky-400/10 text-sky-300";
    case "streamer":
      return "border-amber-400/40 bg-amber-400/10 text-amber-300";
    default:
      return "border-white/15 bg-white/5 text-kos-text/70";
  }
}

export function draftPositionBadgeClass(
  position: string | null | undefined,
): string {
  switch (String(position ?? "").toUpperCase()) {
    case "QB":
      return "border-rose-400/40 bg-rose-400/10 text-rose-300";
    case "RB":
      return "border-edge-green/40 bg-edge-green/10 text-edge-green";
    case "WR":
      return "border-sky-400/40 bg-sky-400/10 text-sky-300";
    case "TE":
      return "border-amber-400/40 bg-amber-400/10 text-amber-300";
    case "K":
      return "border-violet-400/40 bg-violet-400/10 text-violet-300";
    case "DST":
      return "border-slate-300/40 bg-slate-300/10 text-slate-200";
    default:
      return "border-white/15 bg-white/5 text-kos-text/70";
  }
}

export function fantasyPointsPerGame(row: NflFantasyDraftRankingRow): number {
  if (!row.gamesProjected) return 0;
  return row.totalPoints / row.gamesProjected;
}
