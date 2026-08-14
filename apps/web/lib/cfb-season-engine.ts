import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";
import {
  buildProjectGameBody,
  buildSimulateBody,
  parsePowerLadder,
  type CfbPowerLadderRow,
} from "@/lib/cfb-season-engine-format";

export type CfbWeekBoardGame = {
  week: number;
  game_id?: string;
  home: string;
  away: string;
  kickoff?: string;
  neutral_site?: boolean;
  fcs_home?: boolean;
  fcs_away?: boolean;
  fbs_vs_fbs?: boolean;
  conference_game?: boolean;
};

export type CfbTeamDnaRow = {
  team: string;
  conference?: string;
  offense_index?: number | null;
  defense_index?: number | null;
  power_index?: number | null;
  early_season_uncertainty?: number | null;
  qb_class?: string | null;
  qb_name?: string | null;
  open_qb?: boolean;
  efficiency_source?: string | null;
  efficiency_fill?: string | null;
  off_eff?: number | null;
  def_eff?: number | null;
  next?: {
    week?: number;
    opponent?: string;
    home?: boolean;
    neutral_site?: boolean;
  } | null;
};

export type CfbProductDesk = {
  used_in_spread?: boolean;
  kei?: boolean;
  research_only?: boolean;
  week_board?: {
    season?: number;
    weeks?: number[];
    n_games?: number;
    n_fbs_vs_fbs?: number;
    slate_complete?: boolean;
    official?: boolean;
    source?: string;
    used_in_spread?: boolean;
    games?: CfbWeekBoardGame[];
  };
  team_dna?: {
    n?: number;
    official_fbs?: number;
    used_in_spread?: boolean;
    teams?: CfbTeamDnaRow[];
  };
};

export type CfbSeasonEngineStatus = {
  engine_version: string;
  mode?: string;
  scope?: string;
  schedule_source?: string;
  schedule_as_of?: string;
  schedule_game_count?: number;
  n_games?: number;
  slate_complete?: boolean;
  used_in_spread?: boolean;
  team_count?: number;
  roster_source?: string;
  depth_source?: string;
  portal_source?: string;
  returning_source?: string;
  roster_as_of?: string;
  as_of?: string;
  backbone_version?: string;
  n_filled?: number;
  n_thin?: number;
  roster_coverage?: Record<string, unknown>;
  team_codes?: string[];
  team_fidelity_counts?: Record<string, number>;
  layers?: unknown[];
  solid_vs_approximate?: {
    solid?: string[];
    approximate?: string[];
    placeholder_or_deferred?: string[];
  };
  power_style_ladder?: { top?: CfbPowerLadderRow[]; note?: string };
  roster_strength_ladder?: unknown;
  early_season_narrowing?: unknown;
  season_futures?: {
    research_only?: boolean;
    cfp_make?: unknown;
    natty?: unknown;
    win_tables_final?: boolean;
    note?: string;
  };
  desk?: CfbProductDesk;
  data_sources?: Record<string, unknown>;
  entry_points?: Record<string, string>;
  does_not_modify?: string[];
  additive?: boolean;
  error?: string;
};

export type CfbProjectGameResponse = {
  ok?: boolean;
  mode?: string;
  season?: number;
  week?: number;
  game_id?: string;
  home_team?: string;
  away_team?: string;
  engine_version?: string;
  home_win_prob?: number;
  away_win_prob?: number;
  expected_home_score?: number;
  expected_away_score?: number;
  expected_total?: number;
  spread_home?: number;
  margin_sd?: number;
  early_season_uncertainty?: Record<string, unknown>;
  uncertainty?: Record<string, unknown>;
  drivers?: Record<string, unknown>;
  home_layers?: Record<string, unknown>;
  away_layers?: Record<string, unknown>;
  notes?: Record<string, string>;
  fidelity?: string;
  research_prior?: Record<string, unknown>;
  used_in_spread?: boolean;
  error?: string;
  hint?: string;
};

export type CfbSimulateResponse = {
  ok?: boolean;
  mode?: string;
  engine_version?: string;
  n_sims?: number;
  ranking?: Array<Record<string, unknown>>;
  top_teams_by_wins?: Array<Record<string, unknown>>;
  diagnostics?: Record<string, unknown>;
  used_in_spread?: boolean;
  win_tables_final?: boolean;
  cfp_make?: unknown;
  natty?: unknown;
  slate_complete?: boolean;
  error?: string;
};

export type CfbPerformanceSummary = {
  ok?: boolean;
  current_engine_version?: string;
  n_logged?: number;
  n_with_close?: number;
  n_with_result?: number;
  ats?: { record?: string; win_pct?: number | null; n?: number };
  ou?: { record?: string; win_pct?: number | null; n?: number };
  su?: { record?: string; win_pct?: number | null; n?: number };
  clv?: {
    n_spread?: number;
    avg_spread_clv?: number | null;
    spread_clv_positive_rate?: number | null;
    definition?: string;
  };
  error_metrics?: {
    avg_abs_margin_error?: number | null;
    avg_abs_total_error?: number | null;
  };
  recent?: Array<Record<string, unknown>>;
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

export async function fetchCfbSeasonEngineStatus(input?: {
  season?: number;
  asOfWeek?: number;
  demo?: boolean;
}): Promise<CfbSeasonEngineStatus> {
  const base = baseUrl();
  if (!base) {
    return {
      engine_version: "",
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }
  const url = new URL(`${base}/cfb/season-engine/status`);
  url.searchParams.set("season", String(input?.season ?? 2026));
  url.searchParams.set("as_of_week", String(input?.asOfWeek ?? 1));
  url.searchParams.set("demo", String(input?.demo !== false));
  try {
    const res = await upstreamFetch(url.toString(), {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        engine_version: "",
        error: detailError(payload, `Status failed (${res.status})`),
      };
    }
    const solid = payload.solid_vs_approximate;
    return {
      engine_version: String(payload.engine_version ?? ""),
      mode: typeof payload.mode === "string" ? payload.mode : undefined,
      scope: typeof payload.scope === "string" ? payload.scope : undefined,
      schedule_source:
        typeof payload.schedule_source === "string"
          ? payload.schedule_source
          : undefined,
      schedule_as_of:
        typeof payload.schedule_as_of === "string"
          ? payload.schedule_as_of
          : undefined,
      schedule_game_count:
        typeof payload.schedule_game_count === "number"
          ? payload.schedule_game_count
          : undefined,
      n_games:
        typeof payload.n_games === "number"
          ? payload.n_games
          : typeof payload.schedule_game_count === "number"
            ? payload.schedule_game_count
            : undefined,
      slate_complete:
        typeof payload.slate_complete === "boolean"
          ? payload.slate_complete
          : undefined,
      used_in_spread:
        typeof payload.used_in_spread === "boolean"
          ? payload.used_in_spread
          : false,
      team_count:
        typeof payload.team_count === "number" ? payload.team_count : undefined,
      roster_source:
        typeof payload.roster_source === "string"
          ? payload.roster_source
          : undefined,
      depth_source:
        typeof payload.depth_source === "string"
          ? payload.depth_source
          : undefined,
      portal_source:
        typeof payload.portal_source === "string"
          ? payload.portal_source
          : undefined,
      returning_source:
        typeof payload.returning_source === "string"
          ? payload.returning_source
          : undefined,
      roster_as_of:
        typeof payload.roster_as_of === "string"
          ? payload.roster_as_of
          : undefined,
      as_of: typeof payload.as_of === "string" ? payload.as_of : undefined,
      roster_coverage:
        payload.roster_coverage && typeof payload.roster_coverage === "object"
          ? (payload.roster_coverage as Record<string, unknown>)
          : undefined,
      team_codes: Array.isArray(payload.team_codes)
        ? (payload.team_codes as string[])
        : undefined,
      team_fidelity_counts:
        payload.team_fidelity_counts &&
        typeof payload.team_fidelity_counts === "object"
          ? (payload.team_fidelity_counts as Record<string, number>)
          : undefined,
      layers: Array.isArray(payload.layers) ? payload.layers : undefined,
      solid_vs_approximate:
        solid && typeof solid === "object"
          ? (solid as CfbSeasonEngineStatus["solid_vs_approximate"])
          : undefined,
      power_style_ladder:
        payload.power_style_ladder &&
        typeof payload.power_style_ladder === "object"
          ? {
              top: parsePowerLadder(payload.power_style_ladder),
              note:
                typeof (payload.power_style_ladder as { note?: unknown }).note ===
                "string"
                  ? String((payload.power_style_ladder as { note: string }).note)
                  : undefined,
            }
          : undefined,
      roster_strength_ladder: payload.roster_strength_ladder,
      early_season_narrowing: payload.early_season_narrowing,
      backbone_version:
        typeof payload.backbone_version === "string"
          ? payload.backbone_version
          : undefined,
      n_filled:
        typeof payload.n_filled === "number" ? payload.n_filled : undefined,
      n_thin: typeof payload.n_thin === "number" ? payload.n_thin : undefined,
      season_futures:
        payload.season_futures && typeof payload.season_futures === "object"
          ? (payload.season_futures as CfbSeasonEngineStatus["season_futures"])
          : undefined,
      desk:
        payload.desk && typeof payload.desk === "object"
          ? (payload.desk as CfbProductDesk)
          : undefined,
      data_sources:
        payload.data_sources && typeof payload.data_sources === "object"
          ? (payload.data_sources as Record<string, unknown>)
          : undefined,
      entry_points:
        payload.entry_points && typeof payload.entry_points === "object"
          ? (payload.entry_points as Record<string, string>)
          : undefined,
      does_not_modify: Array.isArray(payload.does_not_modify)
        ? (payload.does_not_modify as string[])
        : undefined,
      additive: typeof payload.additive === "boolean" ? payload.additive : undefined,
    };
  } catch (err) {
    return {
      engine_version: "",
      error: err instanceof Error ? err.message : "Status unreachable",
    };
  }
}

export async function fetchCfbProjectGame(input: {
  homeTeam: string;
  awayTeam: string;
  week?: number;
  season?: number;
  neutralSite?: boolean;
  nightGame?: boolean;
  demo?: boolean;
}): Promise<CfbProjectGameResponse> {
  const base = baseUrl();
  if (!base) {
    return { error: "MODEL_SERVICE_URL is not configured." };
  }
  let body: ReturnType<typeof buildProjectGameBody>;
  try {
    body = buildProjectGameBody(input);
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Invalid project-game request",
    };
  }
  try {
    const res = await upstreamFetch(`${base}/cfb/season-engine/project-game`, {
      method: "POST",
      headers: modelHeaders(),
      body: JSON.stringify(body),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        error: detailError(payload, `Project-game failed (${res.status})`),
      };
    }
    if (payload.ok === false || payload.error) {
      return {
        ok: false,
        error: detailError(payload, "Project-game rejected"),
        hint: typeof payload.hint === "string" ? payload.hint : undefined,
        mode: typeof payload.mode === "string" ? payload.mode : undefined,
      };
    }
    return payload as CfbProjectGameResponse;
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Project-game unreachable",
    };
  }
}

export async function fetchCfbPerformance(input?: {
  limit?: number;
  engineVersion?: string;
}): Promise<CfbPerformanceSummary> {
  const base = baseUrl();
  if (!base) {
    return { error: "MODEL_SERVICE_URL is not configured." };
  }
  const url = new URL(`${base}/cfb/season-engine/performance`);
  url.searchParams.set("limit", String(input?.limit ?? 200));
  if (input?.engineVersion) {
    url.searchParams.set("engine_version", input.engineVersion);
  }
  try {
    const res = await upstreamFetch(url.toString(), {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        error: detailError(payload, `Performance failed (${res.status})`),
      };
    }
    const avgError = payload.avg_error;
    const errorMetrics =
      avgError && typeof avgError === "object"
        ? (avgError as CfbPerformanceSummary["error_metrics"])
        : undefined;
    return {
      ok: payload.ok === true,
      current_engine_version:
        typeof payload.current_engine_version === "string"
          ? payload.current_engine_version
          : undefined,
      n_logged:
        typeof payload.n_logged === "number" ? payload.n_logged : undefined,
      n_with_close:
        typeof payload.n_with_close === "number"
          ? payload.n_with_close
          : undefined,
      n_with_result:
        typeof payload.n_with_result === "number"
          ? payload.n_with_result
          : undefined,
      ats:
        payload.ats && typeof payload.ats === "object"
          ? (payload.ats as CfbPerformanceSummary["ats"])
          : undefined,
      ou:
        payload.ou && typeof payload.ou === "object"
          ? (payload.ou as CfbPerformanceSummary["ou"])
          : undefined,
      su:
        payload.su && typeof payload.su === "object"
          ? (payload.su as CfbPerformanceSummary["su"])
          : undefined,
      clv:
        payload.clv && typeof payload.clv === "object"
          ? (payload.clv as CfbPerformanceSummary["clv"])
          : undefined,
      error_metrics: errorMetrics,
      recent: Array.isArray(payload.recent)
        ? (payload.recent as Array<Record<string, unknown>>)
        : undefined,
    };
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Performance unreachable",
    };
  }
}

export async function fetchCfbSimulate(input?: {
  season?: number;
  nSims?: number;
  seed?: number;
  demo?: boolean;
  asOfWeek?: number;
}): Promise<CfbSimulateResponse> {
  const base = baseUrl();
  if (!base) {
    return { error: "MODEL_SERVICE_URL is not configured." };
  }
  let body: ReturnType<typeof buildSimulateBody>;
  try {
    body = buildSimulateBody(input ?? {});
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Invalid simulate request",
    };
  }
  try {
    const res = await upstreamFetch(`${base}/cfb/season-engine/simulate`, {
      method: "POST",
      headers: modelHeaders(),
      body: JSON.stringify(body),
      timeoutMs: UPSTREAM_TIMEOUT_MS.seasonEngine,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return {
        error: detailError(payload, `Simulate failed (${res.status})`),
      };
    }
    return payload as CfbSimulateResponse;
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Simulate unreachable",
    };
  }
}
