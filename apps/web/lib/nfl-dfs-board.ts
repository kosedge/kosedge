import "server-only";
import { env } from "@/lib/config/env";
import {
  canonicalDfsSite,
  filterRowsForRequestedSite,
  type DfsSite,
} from "@/lib/nfl-dfs-identity";

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

function toNum(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function normalizeRow(raw: Record<string, unknown>): NflDfsBoardRow | null {
  const site = canonicalDfsSite(raw.site);
  const salary = toNum(raw.salary);
  const projection = toNum(raw.projection);
  const playerUid = raw.player_uid != null ? String(raw.player_uid) : "";
  const opponent = String(raw.opponent ?? "").trim();
  if (!site || !playerUid || salary == null || salary <= 0 || projection == null) {
    return null;
  }
  if (!opponent) return null;
  const envRaw =
    raw.game_env && typeof raw.game_env === "object"
      ? (raw.game_env as Record<string, unknown>)
      : {};
  return {
    site,
    slateId: String(raw.slate_id ?? ""),
    season: toNum(raw.season) ?? 0,
    week: toNum(raw.week) ?? 0,
    playerUid,
    playerName: String(raw.player_name ?? "Unknown"),
    position: String(raw.position ?? ""),
    team: String(raw.team ?? ""),
    opponent,
    salary,
    projection,
    median: toNum(raw.median),
    floor: toNum(raw.floor),
    ceiling: toNum(raw.ceiling),
    value: toNum(raw.value),
    salaryRelDelta: toNum(raw.salary_rel_delta),
    salaryRelPer1k: toNum(raw.salary_rel_per_1k),
    rankPosition: toNum(raw.rank_position),
    rankOverallValue: toNum(raw.rank_overall_value),
    scoringSystem: String(raw.scoring_system ?? ""),
    productionVersion: String(raw.production_version ?? ""),
    salarySource: String(raw.salary_source ?? ""),
    salarySourceVersion: String(raw.salary_source_version ?? ""),
    salaryCapturedAt: String(raw.salary_captured_at ?? ""),
    ownershipStatus: String(raw.ownership_status ?? "unavailable"),
    leverage: toNum(raw.leverage),
    gameEnv: {
      available: Boolean(envRaw.available),
      reason: String(envRaw.reason ?? "unavailable"),
      total: toNum(envRaw.total),
      spread: toNum(envRaw.spread),
      impliedTeamTotal: toNum(envRaw.implied_team_total),
    },
  };
}

function emptyBoard(
  params: { site: string; season: number; week: number },
  status: string,
  error?: string,
): NflDfsBoardResponse {
  return {
    site: canonicalDfsSite(params.site) ?? params.site,
    season: params.season,
    week: params.week,
    slateId: null,
    status,
    live: false,
    rows: [],
    rejected: [],
    slates: [],
    summary: { topProjection: null, bestValue: null, highestCeiling: null },
    ownership: { status: "unavailable", reason: "no_defensible_source" },
    diagnostics: {
      fail_closed: true,
      season_average_substituted: false,
    },
    error,
  };
}

export async function fetchNflDfsBoard(params: {
  season: number;
  week: number;
  site: string;
  slateId?: string;
  position?: string;
}): Promise<NflDfsBoardResponse> {
  const site = canonicalDfsSite(params.site);
  if (!site) {
    return emptyBoard(params, "invalid_site", "Site must be DK or FD.");
  }
  const base = env.MODEL_SERVICE_URL?.replace(/\/$/, "");
  if (!base) {
    return emptyBoard(
      { ...params, site },
      "unavailable",
      "MODEL_SERVICE_URL is not configured.",
    );
  }
  const url = new URL(`${base}/nfl/dfs/board`);
  url.searchParams.set("season", String(params.season));
  url.searchParams.set("week", String(params.week));
  url.searchParams.set("site", site);
  if (params.slateId) url.searchParams.set("slate_id", params.slateId);
  if (params.position) url.searchParams.set("position", params.position);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
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
      return emptyBoard(
        { ...params, site },
        "unavailable",
        `Model service returned ${response.status}.`,
      );
    }
    const payload = (await response.json()) as Record<string, unknown>;
    const rawRows = Array.isArray(payload.rows) ? payload.rows : [];
    const normalized = rawRows
      .map((row) =>
        row && typeof row === "object"
          ? normalizeRow(row as Record<string, unknown>)
          : null,
      )
      .filter((row): row is NflDfsBoardRow => row != null);
    // Site is a join key. A DK payload cannot render on an FD desk.
    const rows = filterRowsForRequestedSite(normalized, site);
    const summaryRaw =
      payload.summary && typeof payload.summary === "object"
        ? (payload.summary as Record<string, unknown>)
        : {};
    return {
      site,
      season: params.season,
      week: params.week,
      slateId:
        typeof payload.slate_id === "string" ? payload.slate_id : params.slateId ?? null,
      status: String(payload.status ?? (rows.length ? "ok" : "empty")),
      live: false,
      rows,
      rejected: Array.isArray(payload.rejected)
        ? payload.rejected.map((item) => {
            const rec = item as Record<string, unknown>;
            return {
              reason: String(rec.reason ?? "rejected"),
              playerName:
                typeof rec.player_name === "string" ? rec.player_name : null,
            };
          })
        : [],
      slates: Array.isArray(payload.slates)
        ? payload.slates.map((item) => {
            const rec = item as Record<string, unknown>;
            return {
              site: String(rec.site ?? ""),
              slateId: String(rec.slate_id ?? rec.slateId ?? ""),
              week: Number(rec.week ?? params.week),
            };
          })
        : [],
      summary: {
        topProjection: normalizeSummary(summaryRaw.top_projection),
        bestValue: normalizeSummary(summaryRaw.best_value),
        highestCeiling: normalizeSummary(summaryRaw.highest_ceiling),
      },
      ownership: {
        status: "unavailable",
        reason: "no_defensible_source",
      },
      diagnostics:
        payload.diagnostics && typeof payload.diagnostics === "object"
          ? (payload.diagnostics as Record<string, unknown>)
          : { fail_closed: true, season_average_substituted: false },
    };
  } catch {
    return emptyBoard(
      { ...params, site },
      "unavailable",
      "Unable to reach model service.",
    );
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeSummary(raw: unknown): NflDfsSummaryCard | null {
  if (!raw || typeof raw !== "object") return null;
  const rec = raw as Record<string, unknown>;
  const salary = toNum(rec.salary);
  const projection = toNum(rec.projection);
  if (salary == null || projection == null) return null;
  return {
    playerUid: String(rec.player_uid ?? ""),
    playerName: String(rec.player_name ?? ""),
    position: String(rec.position ?? ""),
    team: String(rec.team ?? ""),
    opponent: String(rec.opponent ?? ""),
    salary,
    projection,
    floor: toNum(rec.floor),
    ceiling: toNum(rec.ceiling),
    value: toNum(rec.value),
  };
}

export function formatDfsNumber(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

export function formatSalary(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `$${value.toLocaleString("en-US")}`;
}
