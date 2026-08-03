import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import {
  buildGameBoxesQuery,
  buildSurvivorBody,
  type InjuryPathInput,
  type SeasonEngineMatchupOption,
} from "@/lib/nfl-season-engine-format";

export type { SeasonEngineMatchupOption };

export type SeasonEngineStatus = {
  engine_version: string;
  layers?: unknown[];
  capabilities?: string[];
  contract?: Record<string, unknown>;
  error?: string;
};

export type SeasonEnginePlayerRow = {
  player_key: string;
  player_name: string;
  team: string;
  position: string;
  usage_role?: string;
  personnel?: string;
  script?: string;
  point_estimate: Record<string, number>;
  distributions: Record<
    string,
    { mean: number; std: number; p10: number; p50: number; p90: number }
  >;
};

export type SeasonEngineGameBoxesResponse = {
  mode: string;
  season: number;
  week: number;
  game_id?: string;
  home_team: string;
  away_team: string;
  n_replicates: number;
  engine_version: string;
  game_script_summary?: Record<string, number>;
  notes?: Record<string, string>;
  players: SeasonEnginePlayerRow[];
  diagnostics?: Record<string, unknown>;
  injury_paths?: InjuryPathInput[];
  error?: string;
};

export type SeasonEngineSurvivorPick = {
  team: string;
  week: number;
  win_rate: number;
  win_prob?: number;
  opponent?: string | null;
  home_away?: string | null;
  save_score: number;
  pick_now_score: number;
  future_value?: number;
  plays_this_week?: boolean;
  already_used?: boolean;
  game_id?: string | null;
};

export type SeasonEngineSurvivorResponse = {
  mode: string;
  season: number;
  week: number;
  n_sims: number;
  engine_version: string;
  already_used: string[];
  ranked_picks: SeasonEngineSurvivorPick[];
  all_teams_week?: SeasonEngineSurvivorPick[];
  formula?: Record<string, string>;
  notes?: Record<string, string>;
  diagnostics?: Record<string, unknown>;
  error?: string;
};

function modelHeaders(): HeadersInit {
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...(env.INTERNAL_API_SECRET
      ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
      : {}),
  };
}

function baseUrl(): string | null {
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  return base || null;
}

async function readJson(res: Response): Promise<Record<string, unknown>> {
  try {
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function detailError(payload: Record<string, unknown>, fallback: string): string {
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (typeof d === "string") return d;
        if (d && typeof d === "object" && "msg" in d)
          return String((d as { msg: unknown }).msg);
        return JSON.stringify(d);
      })
      .join("; ");
  }
  if (typeof payload.error === "string") return payload.error;
  return fallback;
}

export async function fetchSeasonEngineStatus(): Promise<SeasonEngineStatus> {
  const base = baseUrl();
  if (!base) {
    return {
      engine_version: "",
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }
  try {
    const res = await upstreamFetch(`${base}/nfl/season-engine/status`, {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        engine_version: "",
        error: detailError(payload, `Status failed (${res.status})`),
      };
    }
    return {
      engine_version: String(payload.engine_version ?? ""),
      layers: Array.isArray(payload.layers) ? payload.layers : undefined,
      capabilities: Array.isArray(payload.capabilities)
        ? (payload.capabilities as string[])
        : undefined,
      contract:
        payload.contract && typeof payload.contract === "object"
          ? (payload.contract as Record<string, unknown>)
          : undefined,
    };
  } catch (err) {
    return {
      engine_version: "",
      error: err instanceof Error ? err.message : "Status unreachable",
    };
  }
}

export async function fetchSeasonEngineGameBoxes(input: {
  homeTeam: string;
  awayTeam: string;
  week?: number;
  season?: number;
  nReplicates?: number;
  seed?: number;
  demo?: boolean;
  includeDiagnostics?: boolean;
  injuryPaths?: InjuryPathInput[];
}): Promise<SeasonEngineGameBoxesResponse> {
  const base = baseUrl();
  if (!base) {
    return {
      mode: "",
      season: 2026,
      week: 1,
      home_team: "",
      away_team: "",
      n_replicates: 0,
      engine_version: "",
      players: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  let query: ReturnType<typeof buildGameBoxesQuery>;
  try {
    query = buildGameBoxesQuery(input);
  } catch (err) {
    return {
      mode: "",
      season: 2026,
      week: 1,
      home_team: "",
      away_team: "",
      n_replicates: 0,
      engine_version: "",
      players: [],
      error: err instanceof Error ? err.message : "Invalid game-boxes request",
    };
  }

  const url = new URL(`${base}/nfl/season-engine/game-boxes`);
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue;
    url.searchParams.set(key, String(value));
  }

  const hasBody = Boolean(input.injuryPaths?.length || input.includeDiagnostics);
  try {
    const res = await upstreamFetch(url.toString(), {
      method: hasBody ? "POST" : "GET",
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.heavy,
      cache: "no-store",
      ...(hasBody
        ? {
            body: JSON.stringify({
              ...(input.injuryPaths?.length
                ? { injury_paths: input.injuryPaths }
                : {}),
              ...(input.includeDiagnostics
                ? { include_diagnostics: true }
                : {}),
            }),
          }
        : {}),
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        mode: "",
        season: query.season,
        week: query.week,
        home_team: query.home_team,
        away_team: query.away_team,
        n_replicates: query.n_replicates,
        engine_version: "",
        players: [],
        error: detailError(payload, `Game boxes failed (${res.status})`),
      };
    }
    return {
      mode: String(payload.mode ?? ""),
      season: Number(payload.season ?? query.season),
      week: Number(payload.week ?? query.week),
      game_id:
        typeof payload.game_id === "string" ? payload.game_id : undefined,
      home_team: String(payload.home_team ?? query.home_team),
      away_team: String(payload.away_team ?? query.away_team),
      n_replicates: Number(payload.n_replicates ?? query.n_replicates),
      engine_version: String(payload.engine_version ?? ""),
      game_script_summary:
        payload.game_script_summary &&
        typeof payload.game_script_summary === "object"
          ? (payload.game_script_summary as Record<string, number>)
          : undefined,
      notes:
        payload.notes && typeof payload.notes === "object"
          ? (payload.notes as Record<string, string>)
          : undefined,
      players: Array.isArray(payload.players)
        ? (payload.players as SeasonEnginePlayerRow[])
        : [],
      diagnostics:
        payload.diagnostics && typeof payload.diagnostics === "object"
          ? (payload.diagnostics as Record<string, unknown>)
          : undefined,
      injury_paths: Array.isArray(payload.injury_paths)
        ? (payload.injury_paths as InjuryPathInput[])
        : undefined,
    };
  } catch (err) {
    return {
      mode: "",
      season: query.season,
      week: query.week,
      home_team: query.home_team,
      away_team: query.away_team,
      n_replicates: query.n_replicates,
      engine_version: "",
      players: [],
      error: err instanceof Error ? err.message : "Game boxes unreachable",
    };
  }
}

export async function fetchSeasonEngineSurvivor(input: {
  week: number;
  alreadyUsed?: string | string[];
  nSims?: number;
  season?: number;
  seed?: number;
  demo?: boolean;
  topN?: number;
  injuryPaths?: InjuryPathInput[];
  includeDiagnostics?: boolean;
}): Promise<SeasonEngineSurvivorResponse> {
  const base = baseUrl();
  if (!base) {
    return {
      mode: "",
      season: 2026,
      week: 1,
      n_sims: 0,
      engine_version: "",
      already_used: [],
      ranked_picks: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const body = buildSurvivorBody(input);
  try {
    const res = await upstreamFetch(`${base}/nfl/season-engine/survivor`, {
      method: "POST",
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.heavy,
      cache: "no-store",
      body: JSON.stringify(body),
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        mode: "",
        season: body.season,
        week: body.week,
        n_sims: body.n_sims,
        engine_version: "",
        already_used: body.already_used,
        ranked_picks: [],
        error: detailError(payload, `Survivor failed (${res.status})`),
      };
    }
    return {
      mode: String(payload.mode ?? ""),
      season: Number(payload.season ?? body.season),
      week: Number(payload.week ?? body.week),
      n_sims: Number(payload.n_sims ?? body.n_sims),
      engine_version: String(payload.engine_version ?? ""),
      already_used: Array.isArray(payload.already_used)
        ? (payload.already_used as string[])
        : body.already_used,
      ranked_picks: Array.isArray(payload.ranked_picks)
        ? (payload.ranked_picks as SeasonEngineSurvivorPick[])
        : [],
      all_teams_week: Array.isArray(payload.all_teams_week)
        ? (payload.all_teams_week as SeasonEngineSurvivorPick[])
        : undefined,
      formula:
        payload.formula && typeof payload.formula === "object"
          ? (payload.formula as Record<string, string>)
          : undefined,
      notes:
        payload.notes && typeof payload.notes === "object"
          ? (payload.notes as Record<string, string>)
          : undefined,
      diagnostics:
        payload.diagnostics && typeof payload.diagnostics === "object"
          ? (payload.diagnostics as Record<string, unknown>)
          : undefined,
    };
  } catch (err) {
    return {
      mode: "",
      season: body.season,
      week: body.week,
      n_sims: body.n_sims,
      engine_version: "",
      already_used: body.already_used,
      ranked_picks: [],
      error: err instanceof Error ? err.message : "Survivor unreachable",
    };
  }
}

/** Upcoming NFL matchups from fair-lines when available. */
export async function loadSeasonEngineMatchups(params?: {
  season?: number;
  daysAhead?: number;
}): Promise<{
  matchups: SeasonEngineMatchupOption[];
  currentWeek: number | null;
  error?: string;
}> {
  const { fetchNflFairLines } = await import("@/lib/nfl-fair-lines");
  const season = params?.season ?? 2026;
  const result = await fetchNflFairLines({
    season,
    daysAhead: params?.daysAhead ?? 21,
    includePastDays: 0,
  });
  if (result.error) {
    return { matchups: [], currentWeek: null, error: result.error };
  }
  const now = Date.now();
  const matchups: SeasonEngineMatchupOption[] = result.lines
    .filter((row) => {
      if (!row.homeAbbr || !row.awayAbbr) return false;
      if (!row.startTime) return true;
      const ts = Date.parse(row.startTime);
      return Number.isFinite(ts) ? ts >= now - 3 * 60 * 60 * 1000 : true;
    })
    .map((row) => ({
      id: row.gameId || `${row.awayAbbr}@${row.homeAbbr}-W${row.week ?? "?"}`,
      label: `${row.awayAbbr} @ ${row.homeAbbr}${
        row.week != null ? ` · W${row.week}` : ""
      }`,
      homeTeam: row.homeAbbr,
      awayTeam: row.awayAbbr,
      week: row.week,
      startTime: row.startTime,
      source: "fair-lines" as const,
    }));
  return {
    matchups,
    currentWeek: result.currentWeek || null,
  };
}
