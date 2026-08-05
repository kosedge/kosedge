import "server-only";
import { env } from "@/lib/config/env";
import { inferHonestEmptySlateStatus } from "@/lib/model-service-status";

export type FantasyScoringProfile = "standard" | "half_ppr" | "ppr";

export const FANTASY_SCORING_PROFILES: Array<{
  value: FantasyScoringProfile;
  label: string;
}> = [
  { value: "standard", label: "Standard" },
  { value: "half_ppr", label: "Half PPR" },
  { value: "ppr", label: "PPR" },
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
  /** Season fantasy-point floor when materializer supplies quantiles. */
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

function toNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function toNumber(value: unknown, fallback = 0): number {
  return toNumberOrNull(value) ?? fallback;
}

function quantilesFromPayload(raw: Record<string, unknown>): {
  floorPoints: number | null;
  medianPoints: number | null;
  ceilingPoints: number | null;
} {
  const payload =
    raw.projection_payload && typeof raw.projection_payload === "object"
      ? (raw.projection_payload as Record<string, unknown>)
      : {};
  return {
    floorPoints:
      toNumberOrNull(raw.floor_points) ?? toNumberOrNull(payload.floor_points),
    medianPoints:
      toNumberOrNull(raw.median_points) ??
      toNumberOrNull(payload.median_points),
    ceilingPoints:
      toNumberOrNull(raw.ceiling_points) ??
      toNumberOrNull(payload.ceiling_points),
  };
}

function normalizeDraftRow(
  raw: Record<string, unknown>,
): NflFantasyDraftRankingRow {
  const quantiles = quantilesFromPayload(raw);
  return {
    season: toNumber(raw.season),
    scoringProfile:
      (raw.scoring_profile as FantasyScoringProfile) ?? "half_ppr",
    modelVersion: String(raw.model_version ?? ""),
    playerId: String(raw.player_id ?? ""),
    playerUid: typeof raw.player_uid === "string" ? raw.player_uid : null,
    playerName: String(raw.player_name ?? "Unknown player"),
    team: String(raw.team ?? "—"),
    position: String(raw.position ?? "—"),
    gamesProjected: toNumber(raw.games_projected),
    passYardsTotal: toNumber(raw.pass_yards_total),
    rushYardsTotal: toNumber(raw.rush_yards_total),
    receivingYardsTotal: toNumber(raw.receiving_yards_total),
    receptionsTotal: toNumber(raw.receptions_total),
    passTdsTotal: toNumber(raw.pass_tds_total),
    rushTdsTotal: toNumber(raw.rush_tds_total),
    recTdsTotal: toNumber(raw.rec_tds_total),
    fieldGoalsMadeTotal: toNumberOrNull(raw.field_goals_made_total),
    fieldGoalsAttemptedTotal: toNumberOrNull(raw.field_goals_attempted_total),
    extraPointsMadeTotal: toNumberOrNull(raw.extra_points_made_total),
    pointsAllowedTotal: toNumberOrNull(raw.points_allowed_total),
    sacksTotal: toNumberOrNull(raw.sacks_total),
    defInterceptionsTotal: toNumberOrNull(raw.def_interceptions_total),
    fumbleRecoveriesTotal: toNumberOrNull(raw.fumble_recoveries_total),
    defensiveTdsTotal: toNumberOrNull(raw.defensive_tds_total),
    safetiesTotal: toNumberOrNull(raw.safeties_total),
    totalPoints: toNumber(raw.total_points),
    floorPoints: quantiles.floorPoints,
    medianPoints: quantiles.medianPoints,
    ceilingPoints: quantiles.ceilingPoints,
    replacementPoints: toNumber(raw.replacement_points),
    valueOverReplacement: toNumber(raw.value_over_replacement),
    rankOverall: toNumber(raw.rank_overall),
    rankPosition: toNumber(raw.rank_position),
    tier: String(raw.tier ?? "bench"),
    isRookie: Boolean(raw.is_rookie),
    rookieYear: toNumberOrNull(raw.rookie_year),
    draftNumber: toNumberOrNull(raw.draft_number),
    updatedAt: typeof raw.updated_at === "string" ? raw.updated_at : null,
  };
}

export async function fetchNflFantasyDraftRankings(params: {
  season: number;
  scoringProfile?: FantasyScoringProfile;
  modelVersion?: string;
  position?: string;
  tier?: string;
  rookiesOnly?: boolean;
  limit?: number;
}): Promise<NflFantasyDraftRankingsResponse> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) {
    return {
      count: 0,
      rows: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/nfl/fantasy/draft-rankings`);
  url.searchParams.set("season", String(params.season));
  url.searchParams.set("scoring_profile", params.scoringProfile ?? "half_ppr");
  url.searchParams.set("model_version", params.modelVersion ?? "nfl-player-v1");
  if (params.position && params.position.trim().length > 0) {
    url.searchParams.set("position", params.position.trim().toUpperCase());
  }
  if (params.tier && params.tier.trim().length > 0) {
    url.searchParams.set("tier", params.tier.trim());
  }
  if (params.rookiesOnly) {
    url.searchParams.set("rookies_only", "true");
  }
  url.searchParams.set("limit", String(params.limit ?? 300));

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(url.toString(), {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) {
      const statusError = `Model service returned ${response.status}.`;
      const honestStatus = inferHonestEmptySlateStatus({
        season: params.season,
        error: statusError,
      });
      return {
        count: 0,
        rows: [],
        slateStatus: honestStatus ?? undefined,
        error: honestStatus ? undefined : statusError,
      };
    }
    const payload = (await response.json()) as {
      count?: number;
      rows?: Array<Record<string, unknown>>;
    };
    const rows = Array.isArray(payload.rows)
      ? payload.rows.map(normalizeDraftRow)
      : [];
    return {
      count: typeof payload.count === "number" ? payload.count : rows.length,
      rows,
      slateStatus: rows.length === 0 ? "no_projections_yet" : "ok",
    };
  } catch (cause) {
    const transportError = "Unable to reach model service.";
    const honestStatus = inferHonestEmptySlateStatus({
      season: params.season,
      error: transportError,
      cause,
    });
    return {
      count: 0,
      rows: [],
      slateStatus: honestStatus ?? undefined,
      error: honestStatus ? undefined : transportError,
    };
  } finally {
    clearTimeout(timeout);
  }
}

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
