import type { FantasyDeskRow, FantasyScoringProfile } from "@/lib/fantasy/types";

export type MockTeamCount = 10 | 12;

export type MockCpuPersona =
  | "balanced"
  | "adp_follower"
  | "value_hunter"
  | "need_first";

export type MockDraftConfig = {
  teamCount: MockTeamCount;
  scoringProfile: FantasyScoringProfile;
  /** 1-indexed draft slot for the human. */
  userSlot: number;
  /** Total snake rounds (starters + bench). */
  rounds: number;
};

export type MockDraftPick = {
  overall: number;
  round: number;
  pickInRound: number;
  teamIndex: number;
  playerId: string;
  playerName: string;
  position: string;
  team: string;
  isUser: boolean;
  /** Snapshot at pick time for post-draft analysis. */
  modelRank: number;
  adp: number | null;
  valueDelta: number | null;
};

export type MockDraftPhase = "setup" | "live" | "results";

export type MockDraftState = {
  config: MockDraftConfig;
  phase: MockDraftPhase;
  picks: MockDraftPick[];
  /** 1-indexed next overall pick. */
  nextOverall: number;
  totalPicks: number;
  personas: MockCpuPersona[];
  teamNames: string[];
  draftedIds: string[];
  modelVersion: string;
  season: number;
  boardSource: FantasyDeskRow["source"] | "empty";
  startedAt: string;
};

export type MockPostDraftReport = {
  grade: string;
  detail: string;
  starterPoints: number;
  strengths: string[];
  weaknesses: string[];
  values: string[];
  reaches: string[];
  roster: FantasyDeskRow[];
};

export const MOCK_ROUNDS = 15;

/** Standard single-QB starter needs; K/DST zeroed when board lacks them. */
export const MOCK_STARTER_NEEDS: Record<string, number> = {
  QB: 1,
  RB: 2,
  WR: 2,
  TE: 1,
  FLEX: 1,
  K: 1,
  DST: 1,
};

export const MOCK_CPU_WEIGHTS: Record<
  MockCpuPersona,
  { adp: number; value: number; need: number; rank: number }
> = {
  balanced: { adp: 1.0, value: 0.85, need: 1.1, rank: 0.7 },
  adp_follower: { adp: 1.45, value: 0.45, need: 0.95, rank: 0.55 },
  value_hunter: { adp: 0.65, value: 1.45, need: 1.0, rank: 0.9 },
  need_first: { adp: 0.8, value: 0.7, need: 1.5, rank: 0.75 },
};
