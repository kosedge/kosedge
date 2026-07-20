import "server-only";
import { env } from "@/lib/config/env";

export type TendencyPerspective = "offense" | "defense";
export type TendencySituationType = "down_distance" | "score_state" | "field_position";
export type QbSituationType = "overall" | "down_type" | "pressure" | "score_state" | "field_position";

export type NflTeamSituationalTendencyRow = {
  season: number;
  team: string;
  perspective: TendencyPerspective;
  situationType: string;
  situationBucket: string;
  plays: number;
  passPlays: number;
  rushPlays: number;
  passRate: number;
  dropbackPlays: number;
  dropbackRate: number;
  avgXpass: number;
  passRateOverExpected: number;
  shotgunPlays: number;
  shotgunRate: number;
  noHuddlePlays: number;
  noHuddleRate: number;
  epaPerPlay: number;
  successRate: number;
  explosivePlayRate: number;
  sackRate: number;
  computedAt: string | null;
};

export type NflTeamDirectionTendencyRow = {
  season: number;
  team: string;
  perspective: TendencyPerspective;
  passPlaysWithLocation: number;
  passLeftRate: number;
  passMiddleRate: number;
  passRightRate: number;
  runPlaysWithLocation: number;
  runLeftRate: number;
  runMiddleRate: number;
  runRightRate: number;
  runPlaysWithGap: number;
  runEndRate: number;
  runGuardRate: number;
  runTackleRate: number;
  computedAt: string | null;
};

export type NflQbSituationalSplitRow = {
  season: number;
  playerId: string;
  playerName: string;
  team: string;
  situationType: string;
  situationBucket: string;
  dropbacks: number;
  passAttempts: number;
  completions: number;
  completionRate: number;
  passYards: number;
  yardsPerAttempt: number;
  epaPerPlay: number;
  successRate: number;
  avgCp: number;
  cpoe: number;
  sacks: number;
  sackRate: number;
  interceptions: number;
  interceptionRate: number;
  passingTds: number;
  tdRate: number;
  computedAt: string | null;
};

export type NflTeamTendencyProfileResponse = {
  season: number;
  team: string;
  perspective: TendencyPerspective;
  situational: NflTeamSituationalTendencyRow[];
  direction: NflTeamDirectionTendencyRow | null;
  error?: string;
};

export type NflQbSituationalSplitsResponse = {
  count: number;
  rows: NflQbSituationalSplitRow[];
  error?: string;
};

/** Real tendency analytics need at least a full season of played PBP -- the
 * current/future season (e.g. preseason 2026) has no rows yet, so callers
 * should try recent completed seasons first via `TENDENCY_SEASON_FALLBACKS`. */
export const TENDENCY_SEASON_FALLBACKS = [2025, 2024, 2023];

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function normalizeSituational(raw: Record<string, unknown>): NflTeamSituationalTendencyRow {
  return {
    season: toNumber(raw.season),
    team: String(raw.team ?? "—"),
    perspective: raw.perspective === "defense" ? "defense" : "offense",
    situationType: String(raw.situation_type ?? ""),
    situationBucket: String(raw.situation_bucket ?? ""),
    plays: toNumber(raw.plays),
    passPlays: toNumber(raw.pass_plays),
    rushPlays: toNumber(raw.rush_plays),
    passRate: toNumber(raw.pass_rate),
    dropbackPlays: toNumber(raw.dropback_plays),
    dropbackRate: toNumber(raw.dropback_rate),
    avgXpass: toNumber(raw.avg_xpass),
    passRateOverExpected: toNumber(raw.pass_rate_over_expected),
    shotgunPlays: toNumber(raw.shotgun_plays),
    shotgunRate: toNumber(raw.shotgun_rate),
    noHuddlePlays: toNumber(raw.no_huddle_plays),
    noHuddleRate: toNumber(raw.no_huddle_rate),
    epaPerPlay: toNumber(raw.epa_per_play),
    successRate: toNumber(raw.success_rate),
    explosivePlayRate: toNumber(raw.explosive_play_rate),
    sackRate: toNumber(raw.sack_rate),
    computedAt: typeof raw.computed_at === "string" ? raw.computed_at : null,
  };
}

function normalizeDirection(raw: Record<string, unknown>): NflTeamDirectionTendencyRow {
  return {
    season: toNumber(raw.season),
    team: String(raw.team ?? "—"),
    perspective: raw.perspective === "defense" ? "defense" : "offense",
    passPlaysWithLocation: toNumber(raw.pass_plays_with_location),
    passLeftRate: toNumber(raw.pass_left_rate),
    passMiddleRate: toNumber(raw.pass_middle_rate),
    passRightRate: toNumber(raw.pass_right_rate),
    runPlaysWithLocation: toNumber(raw.run_plays_with_location),
    runLeftRate: toNumber(raw.run_left_rate),
    runMiddleRate: toNumber(raw.run_middle_rate),
    runRightRate: toNumber(raw.run_right_rate),
    runPlaysWithGap: toNumber(raw.run_plays_with_gap),
    runEndRate: toNumber(raw.run_end_rate),
    runGuardRate: toNumber(raw.run_guard_rate),
    runTackleRate: toNumber(raw.run_tackle_rate),
    computedAt: typeof raw.computed_at === "string" ? raw.computed_at : null,
  };
}

function normalizeQbSplit(raw: Record<string, unknown>): NflQbSituationalSplitRow {
  return {
    season: toNumber(raw.season),
    playerId: String(raw.player_id ?? ""),
    playerName: String(raw.player_name ?? "Unknown"),
    team: String(raw.team ?? "—"),
    situationType: String(raw.situation_type ?? ""),
    situationBucket: String(raw.situation_bucket ?? ""),
    dropbacks: toNumber(raw.dropbacks),
    passAttempts: toNumber(raw.pass_attempts),
    completions: toNumber(raw.completions),
    completionRate: toNumber(raw.completion_rate),
    passYards: toNumber(raw.pass_yards),
    yardsPerAttempt: toNumber(raw.yards_per_attempt),
    epaPerPlay: toNumber(raw.epa_per_play),
    successRate: toNumber(raw.success_rate),
    avgCp: toNumber(raw.avg_cp),
    cpoe: toNumber(raw.cpoe),
    sacks: toNumber(raw.sacks),
    sackRate: toNumber(raw.sack_rate),
    interceptions: toNumber(raw.interceptions),
    interceptionRate: toNumber(raw.interception_rate),
    passingTds: toNumber(raw.passing_tds),
    tdRate: toNumber(raw.td_rate),
    computedAt: typeof raw.computed_at === "string" ? raw.computed_at : null,
  };
}

async function fetchJson(path: string, searchParams: Record<string, string | number | boolean | undefined>) {
  const base = env.MODEL_SERVICE_URL;
  if (!base) return { ok: false as const, error: "MODEL_SERVICE_URL is not configured." };

  const url = new URL(`${base.replace(/\/+$/, "")}${path}`);
  for (const [key, value] of Object.entries(searchParams)) {
    if (value === undefined || value === null || value === "") continue;
    url.searchParams.set(key, String(value));
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(url.toString(), {
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET ? { "x-kosedge-secret": env.INTERNAL_API_SECRET } : {}),
      },
    });
    if (!response.ok) {
      return { ok: false as const, error: `Model service returned ${response.status}.` };
    }
    const payload = (await response.json()) as Record<string, unknown>;
    return { ok: true as const, payload };
  } catch {
    return { ok: false as const, error: "Unable to reach model service." };
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchNflTeamTendencyProfile(params: {
  season: number;
  team: string;
  perspective?: TendencyPerspective;
  situationType?: TendencySituationType;
}): Promise<NflTeamTendencyProfileResponse> {
  const perspective = params.perspective ?? "offense";
  const result = await fetchJson("/nfl/tendencies/team", {
    season: params.season,
    team: params.team,
    perspective,
    situation_type: params.situationType,
  });
  if (!result.ok) {
    return { season: params.season, team: params.team, perspective, situational: [], direction: null, error: result.error };
  }
  const situationalRaw = Array.isArray(result.payload.situational)
    ? (result.payload.situational as Array<Record<string, unknown>>)
    : [];
  const directionRaw = result.payload.direction as Record<string, unknown> | null | undefined;
  return {
    season: params.season,
    team: params.team,
    perspective,
    situational: situationalRaw.map(normalizeSituational),
    direction: directionRaw ? normalizeDirection(directionRaw) : null,
  };
}

/** Walks backward through real completed seasons (never the current/future
 * season with no played PBP yet) until it finds a season with actual
 * tendency rows for this team/perspective, so a preseason page load doesn't
 * silently render an empty board. */
export async function fetchNflTeamTendencyProfileResolved(params: {
  season: number;
  team: string;
  perspective?: TendencyPerspective;
}): Promise<NflTeamTendencyProfileResponse & { requestedSeason: number; usedFallback: boolean }> {
  const candidateSeasons = [params.season, ...TENDENCY_SEASON_FALLBACKS.filter((s) => s !== params.season)];
  let lastResult: NflTeamTendencyProfileResponse | null = null;
  for (const season of candidateSeasons) {
    const result = await fetchNflTeamTendencyProfile({ season, team: params.team, perspective: params.perspective });
    lastResult = result;
    if (result.situational.length > 0 || result.direction) {
      return { ...result, requestedSeason: params.season, usedFallback: season !== params.season };
    }
    if (result.error) break;
  }
  return {
    ...(lastResult ?? {
      season: params.season,
      team: params.team,
      perspective: params.perspective ?? "offense",
      situational: [],
      direction: null,
    }),
    requestedSeason: params.season,
    usedFallback: false,
  };
}

export async function fetchNflQbSituationalSplits(params: {
  season: number;
  team?: string;
  playerId?: string;
  situationType?: QbSituationType;
  minDropbacks?: number;
  limit?: number;
}): Promise<NflQbSituationalSplitsResponse> {
  const result = await fetchJson("/nfl/tendencies/qb", {
    season: params.season,
    team: params.team,
    player_id: params.playerId,
    situation_type: params.situationType,
    min_dropbacks: params.minDropbacks ?? 0,
    limit: params.limit ?? 500,
  });
  if (!result.ok) return { count: 0, rows: [], error: result.error };
  const rows = Array.isArray(result.payload.rows) ? (result.payload.rows as Array<Record<string, unknown>>).map(normalizeQbSplit) : [];
  return { count: typeof result.payload.count === "number" ? result.payload.count : rows.length, rows };
}

export const SITUATION_BUCKET_LABELS: Record<string, string> = {
  early_down_short: "Early down, short (1-3)",
  early_down_medium: "Early down, medium (4-6)",
  early_down_long: "Early down, long (7+)",
  third_fourth_short: "3rd/4th short (1-3)",
  third_fourth_medium: "3rd/4th medium (4-6)",
  third_fourth_long: "3rd/4th long (7+)",
  leading_big: "Leading big (14+)",
  leading_small: "Leading small (1-13)",
  tied: "Tied",
  trailing_small: "Trailing small (1-13)",
  trailing_big: "Trailing big (14+)",
  own_territory: "Own territory",
  midfield: "Midfield",
  red_zone: "Red zone",
  goal_to_go: "Goal-to-go",
  overall: "Overall",
  early_down: "Early down (1st/2nd)",
  money_down: "Money down (3rd/4th)",
  clean_pocket: "Clean pocket",
  pressure: "Under pressure",
};

export function situationBucketLabel(bucket: string): string {
  return SITUATION_BUCKET_LABELS[bucket] ?? bucket.replace(/_/g, " ");
}

export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSigned(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}
