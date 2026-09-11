import type { DfsSite } from "@/lib/nfl-dfs-identity";

export type NflDfsBoardRow = {
  site: DfsSite;
  slateId: string;
  season: number;
  week: number;
  playerUid: string;
  playerName: string;
  position: string;
  team: string;
  opponent: string;
  salary: number;
  projection: number;
  median: number | null;
  floor: number | null;
  ceiling: number | null;
  value: number | null;
  salaryRelDelta: number | null;
  salaryRelPer1k: number | null;
  rankPosition: number | null;
  rankOverallValue: number | null;
  scoringSystem: string;
  productionVersion: string;
  salarySource: string;
  salarySourceVersion: string;
  salaryCapturedAt: string;
  ownershipStatus: string;
  leverage: number | null;
  gameEnv: {
    available: boolean;
    reason: string;
    total: number | null;
    spread: number | null;
    impliedTeamTotal: number | null;
  };
};

export type NflDfsSummaryCard = {
  playerUid: string;
  playerName: string;
  position: string;
  team: string;
  opponent: string;
  salary: number;
  projection: number;
  floor: number | null;
  ceiling: number | null;
  value: number | null;
};

export type NflDfsBoardResponse = {
  site: DfsSite | string;
  season: number;
  week: number;
  slateId: string | null;
  status: string;
  live: boolean;
  rows: NflDfsBoardRow[];
  rejected: Array<{ reason: string; playerName?: string | null }>;
  slates: Array<{ site: string; slateId: string; week: number }>;
  summary: {
    topProjection: NflDfsSummaryCard | null;
    bestValue: NflDfsSummaryCard | null;
    highestCeiling: NflDfsSummaryCard | null;
  };
  ownership: { status: string; reason: string };
  diagnostics: Record<string, unknown>;
  error?: string;
};

export function formatDfsNumber(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

export function formatSalary(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `$${value.toLocaleString("en-US")}`;
}
