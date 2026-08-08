/**
 * NFL True PR product surface — types + BFF fetch + display helpers.
 * Display/copy only; engine math stays upstream.
 */

import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type TruePrDriverChip = {
  available: boolean;
  band?: string | null;
  label?: string | null;
  band_label?: string | null;
  reason?: string | null;
  approximate?: boolean;
  fidelity?: string | null;
  framing?: string | null;
  intrinsic_pr_unchanged?: boolean;
  state?: string | null;
  w_prior?: number | null;
  w_current?: number | null;
  games_played?: number | null;
  starter_name?: string | null;
  tenure?: string | null;
  same_as_prior?: boolean | null;
  premium?: number | null;
  score?: number | null;
  preseason?: boolean;
  early_season?: boolean;
  stub?: string | null;
  source?: string | null;
};

export type TruePrTeamRow = {
  team: string;
  rank: number;
  intrinsic_pr: number;
  full_strength_offense_index: number;
  full_strength_defense_index: number;
  offense_index: number;
  defense_index: number;
  drivers: {
    continuity: TruePrDriverChip;
    qb_premium: TruePrDriverChip;
    past_sos: TruePrDriverChip;
    projected_sos_2026: TruePrDriverChip;
    blend: TruePrDriverChip;
  };
};

export type TruePrProductSurface = {
  product_version: string;
  engine_version: string;
  season: number;
  as_of_week: number;
  mode: string;
  schedule_source?: string;
  strength_source?: string;
  team_count: number;
  contract?: Record<string, string>;
  copy_rules?: Record<string, string>;
  teams: TruePrTeamRow[];
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

function asDriver(raw: unknown): TruePrDriverChip {
  if (!raw || typeof raw !== "object") {
    return { available: false, label: "unavailable", approximate: true };
  }
  const d = raw as Record<string, unknown>;
  return {
    available: Boolean(d.available),
    band: typeof d.band === "string" ? d.band : null,
    label: typeof d.label === "string" ? d.label : null,
    band_label: typeof d.band_label === "string" ? d.band_label : null,
    reason: typeof d.reason === "string" ? d.reason : null,
    approximate: Boolean(d.approximate),
    fidelity: typeof d.fidelity === "string" ? d.fidelity : null,
    framing: typeof d.framing === "string" ? d.framing : null,
    intrinsic_pr_unchanged: Boolean(d.intrinsic_pr_unchanged),
    state: typeof d.state === "string" ? d.state : null,
    w_prior: typeof d.w_prior === "number" ? d.w_prior : null,
    w_current: typeof d.w_current === "number" ? d.w_current : null,
    games_played:
      typeof d.games_played === "number" ? d.games_played : null,
    starter_name: typeof d.starter_name === "string" ? d.starter_name : null,
    tenure: typeof d.tenure === "string" ? d.tenure : null,
    same_as_prior:
      typeof d.same_as_prior === "boolean" ? d.same_as_prior : null,
    premium: typeof d.premium === "number" ? d.premium : null,
    score: typeof d.score === "number" ? d.score : null,
    preseason: Boolean(d.preseason),
    early_season: Boolean(d.early_season),
    stub: typeof d.stub === "string" ? d.stub : null,
    source: typeof d.source === "string" ? d.source : null,
  };
}

function asTeamRow(raw: unknown): TruePrTeamRow | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const team = typeof r.team === "string" ? r.team : "";
  if (!team) return null;
  const driversRaw =
    r.drivers && typeof r.drivers === "object"
      ? (r.drivers as Record<string, unknown>)
      : {};
  return {
    team,
    rank: typeof r.rank === "number" ? r.rank : 0,
    intrinsic_pr: typeof r.intrinsic_pr === "number" ? r.intrinsic_pr : 1,
    full_strength_offense_index:
      typeof r.full_strength_offense_index === "number"
        ? r.full_strength_offense_index
        : 1,
    full_strength_defense_index:
      typeof r.full_strength_defense_index === "number"
        ? r.full_strength_defense_index
        : 1,
    offense_index:
      typeof r.offense_index === "number" ? r.offense_index : 1,
    defense_index:
      typeof r.defense_index === "number" ? r.defense_index : 1,
    drivers: {
      continuity: asDriver(driversRaw.continuity),
      qb_premium: asDriver(driversRaw.qb_premium),
      past_sos: asDriver(driversRaw.past_sos),
      projected_sos_2026: asDriver(driversRaw.projected_sos_2026),
      blend: asDriver(driversRaw.blend),
    },
  };
}

export async function fetchTruePrProductSurface(options?: {
  season?: number;
  asOfWeek?: number;
  team?: string | null;
}): Promise<TruePrProductSurface> {
  const base = baseUrl();
  if (!base) {
    return {
      product_version: "",
      engine_version: "",
      season: options?.season ?? 2026,
      as_of_week: options?.asOfWeek ?? 1,
      mode: "",
      team_count: 0,
      teams: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }
  try {
    const url = new URL(`${base}/nfl/season-engine/true-pr`);
    url.searchParams.set("season", String(options?.season ?? 2026));
    url.searchParams.set("as_of_week", String(options?.asOfWeek ?? 1));
    if (options?.team) url.searchParams.set("team", options.team);
    const res = await upstreamFetch(url.toString(), {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : typeof payload.error === "string"
            ? payload.error
            : `True PR fetch failed (${res.status})`;
      return {
        product_version: "",
        engine_version: "",
        season: options?.season ?? 2026,
        as_of_week: options?.asOfWeek ?? 1,
        mode: "",
        team_count: 0,
        teams: [],
        error: detail,
      };
    }
    const teams = Array.isArray(payload.teams)
      ? payload.teams
          .map(asTeamRow)
          .filter((row): row is TruePrTeamRow => row != null)
      : [];
    return {
      product_version: String(payload.product_version ?? ""),
      engine_version: String(payload.engine_version ?? ""),
      season:
        typeof payload.season === "number"
          ? payload.season
          : (options?.season ?? 2026),
      as_of_week:
        typeof payload.as_of_week === "number"
          ? payload.as_of_week
          : (options?.asOfWeek ?? 1),
      mode: typeof payload.mode === "string" ? payload.mode : "",
      schedule_source:
        typeof payload.schedule_source === "string"
          ? payload.schedule_source
          : undefined,
      strength_source:
        typeof payload.strength_source === "string"
          ? payload.strength_source
          : undefined,
      team_count:
        typeof payload.team_count === "number"
          ? payload.team_count
          : teams.length,
      contract:
        payload.contract && typeof payload.contract === "object"
          ? (payload.contract as Record<string, string>)
          : undefined,
      copy_rules:
        payload.copy_rules && typeof payload.copy_rules === "object"
          ? (payload.copy_rules as Record<string, string>)
          : undefined,
      teams,
      error: typeof payload.error === "string" ? payload.error : undefined,
    };
  } catch (err) {
    return {
      product_version: "",
      engine_version: "",
      season: options?.season ?? 2026,
      as_of_week: options?.asOfWeek ?? 1,
      mode: "",
      team_count: 0,
      teams: [],
      error: err instanceof Error ? err.message : "True PR unreachable",
    };
  }
}

/** Title-case band labels for chips. */
export function formatDriverBand(band: string | null | undefined): string {
  if (!band) return "—";
  return band
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
