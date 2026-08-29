import "server-only";
import { env } from "@/lib/config/env";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type ModelTrackerPick = {
  id: string;
  sport: string;
  season: number;
  week: number;
  game_key?: string;
  home_team?: string;
  away_team?: string;
  market_type?: string;
  side?: string;
  line_at_publish?: number | null;
  line_at_close?: number | null;
  tag?: "PLAY" | "LEAN" | string;
  units?: number;
  grade?: string;
  units_pnl?: number;
  clv?: number | null;
  edge_pts?: number | null;
  engine_version?: string | null;
  kei_version?: string | null;
  published_at?: string;
  graded_at?: string | null;
  [key: string]: unknown;
};

export type ModelTrackerSummary = {
  ok?: boolean;
  n?: number;
  plays?: Record<string, unknown>;
  leans?: Record<string, unknown>;
  units?: {
    n_plays?: number;
    units_risked?: number;
    units_pending?: number;
    units_won?: number;
    units_lost?: number;
    units_net?: number;
    roi?: number | null;
  };
  unit_curve?: Array<{
    id?: string;
    game_key?: string;
    graded_at?: string;
    grade?: string;
    units_pnl?: number;
    cumulative_units?: number;
  }>;
  clv?: {
    n?: number;
    avg_clv?: number | null;
    positive_rate?: number | null;
  };
  by_engine?: Record<string, Record<string, unknown>>;
  by_week?: Record<string, Record<string, unknown>>;
  recent?: ModelTrackerPick[];
  tracking?: Record<string, unknown>;
  error?: string;
};

export type ModelTrackerStatus = {
  ok?: boolean;
  healthy?: boolean;
  n_picks?: number;
  n_pending?: number;
  n_plays?: number;
  n_leans?: number;
  unit_rules?: { PLAY?: number; LEAN?: number };
  tracker_version?: string;
  sports?: Record<string, unknown>;
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

export async function fetchModelTrackerStatus(): Promise<ModelTrackerStatus> {
  const base = baseUrl();
  if (!base) return { error: "MODEL_SERVICE_URL is not configured." };
  try {
    const res = await upstreamFetch(`${base}/model-tracker/status`, {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.fast,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return { error: `Tracker status failed (${res.status})` };
    }
    return payload as ModelTrackerStatus;
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Tracker unreachable",
    };
  }
}

export async function fetchModelTrackerSummary(input?: {
  sport?: string;
  season?: number;
  week?: number;
  engineVersion?: string;
  limit?: number;
}): Promise<ModelTrackerSummary> {
  const base = baseUrl();
  if (!base) return { error: "MODEL_SERVICE_URL is not configured." };
  const url = new URL(`${base}/model-tracker/summary`);
  if (input?.sport) url.searchParams.set("sport", input.sport);
  if (input?.season != null) url.searchParams.set("season", String(input.season));
  if (input?.week != null) url.searchParams.set("week", String(input.week));
  if (input?.engineVersion) {
    url.searchParams.set("engine_version", input.engineVersion);
  }
  url.searchParams.set("limit", String(input?.limit ?? 1000));
  try {
    const res = await upstreamFetch(url.toString(), {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return { error: `Tracker summary failed (${res.status})` };
    }
    return payload as ModelTrackerSummary;
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Tracker unreachable",
    };
  }
}

export async function fetchModelTrackerPicks(input?: {
  sport?: string;
  season?: number;
  week?: number;
  tag?: string;
  grade?: string;
  limit?: number;
}): Promise<{ ok?: boolean; picks?: ModelTrackerPick[]; n?: number; error?: string }> {
  const base = baseUrl();
  if (!base) return { error: "MODEL_SERVICE_URL is not configured." };
  const url = new URL(`${base}/model-tracker/picks`);
  if (input?.sport) url.searchParams.set("sport", input.sport);
  if (input?.season != null) url.searchParams.set("season", String(input.season));
  if (input?.week != null) url.searchParams.set("week", String(input.week));
  if (input?.tag) url.searchParams.set("tag", input.tag);
  if (input?.grade) url.searchParams.set("grade", input.grade);
  url.searchParams.set("limit", String(input?.limit ?? 100));
  try {
    const res = await upstreamFetch(url.toString(), {
      headers: modelHeaders(),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok) {
      return { error: `Tracker picks failed (${res.status})` };
    }
    return {
      ok: payload.ok === true,
      n: typeof payload.n === "number" ? payload.n : undefined,
      picks: Array.isArray(payload.picks)
        ? (payload.picks as ModelTrackerPick[])
        : [],
    };
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Tracker unreachable",
    };
  }
}

export type LogPickInput = {
  sport: string;
  season: number;
  week: number;
  home_team: string;
  away_team: string;
  market_type: string;
  side: string;
  tag: "PLAY" | "LEAN";
  line_at_publish?: number;
  odds_american?: number;
  game_id?: string;
  engine_version?: string;
  kei_version?: string;
  edge_pts?: number;
  notes?: string;
};

export async function postModelTrackerPick(
  body: LogPickInput,
): Promise<{ ok?: boolean; pick?: ModelTrackerPick; error?: string }> {
  const base = baseUrl();
  if (!base) return { error: "MODEL_SERVICE_URL is not configured." };
  try {
    const res = await upstreamFetch(`${base}/model-tracker/picks`, {
      method: "POST",
      headers: modelHeaders(),
      body: JSON.stringify({
        ...body,
        created_by: "desk",
        source: "manual",
      }),
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      cache: "no-store",
    });
    const payload = await readJson(res);
    if (!res.ok || payload.ok === false) {
      return {
        error:
          typeof payload.error === "string"
            ? payload.error
            : `Log pick failed (${res.status})`,
      };
    }
    return {
      ok: true,
      pick: payload.pick as ModelTrackerPick,
    };
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Tracker unreachable",
    };
  }
}

export async function postModelTrackerGrade(input: {
  pickId: string;
  home_score: number;
  away_score: number;
}): Promise<{ ok?: boolean; pick?: ModelTrackerPick; error?: string }> {
  const base = baseUrl();
  if (!base) return { error: "MODEL_SERVICE_URL is not configured." };
  try {
    const res = await upstreamFetch(
      `${base}/model-tracker/picks/${input.pickId}/grade`,
      {
        method: "POST",
        headers: modelHeaders(),
        body: JSON.stringify({
          home_score: input.home_score,
          away_score: input.away_score,
          source: "manual",
        }),
        timeoutMs: UPSTREAM_TIMEOUT_MS.board,
        cache: "no-store",
      },
    );
    const payload = await readJson(res);
    if (!res.ok || payload.ok === false) {
      return {
        error:
          typeof payload.error === "string"
            ? payload.error
            : `Grade failed (${res.status})`,
      };
    }
    return { ok: true, pick: payload.pick as ModelTrackerPick };
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Tracker unreachable",
    };
  }
}
