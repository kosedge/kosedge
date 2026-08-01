import "server-only";
import { env } from "@/lib/config/env";
import {
  type WnbaFairLineRow,
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  formatWinProb,
} from "@/lib/wnba-fair-lines-format";
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

export type { WnbaFairLineRow };
export {
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  formatWinProb,
};

export type WnbaFairLinesResponse = {
  gameDate: string;
  modelVersion: string;
  workerBuildId: string;
  count: number;
  lines: WnbaFairLineRow[];
  slateStatus: string;
  message?: string;
  phase?: string;
  error?: string;
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

function toIsoOrNull(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (value instanceof Date) return value.toISOString();
  return null;
}

function fairAwayFromHome(homeMl: number | null): number | null {
  if (homeMl === null || !Number.isFinite(homeMl) || homeMl === 0) return null;
  if (homeMl > 0) return -homeMl;
  return Math.abs(homeMl);
}

function normalizeFairLine(
  raw: Record<string, unknown>,
  modelVersion: string,
): WnbaFairLineRow {
  const fairHomeMl = toNumberOrNull(raw.fair_home_ml);
  return {
    gameId: String(raw.game_id ?? ""),
    gameDate: toIsoOrNull(raw.game_date),
    startTime: toIsoOrNull(raw.start_time),
    homeTeam: String(raw.home_team ?? "Home"),
    awayTeam: String(raw.away_team ?? "Away"),
    homeWinProb: toNumberOrNull(raw.home_win_prob),
    fairHomeMl,
    fairAwayMl: fairAwayFromHome(fairHomeMl),
    totalMean: toNumberOrNull(raw.total_mean),
    fairTotal: toNumberOrNull(raw.fair_total),
    fairSpreadHome: toNumberOrNull(raw.fair_spread_home),
    homeCoverProb: toNumberOrNull(raw.home_cover_prob),
    marginMean: toNumberOrNull(raw.margin_mean),
    projectedAt: toIsoOrNull(raw.projected_at),
    modelVersion,
    workerBuildId:
      typeof raw.worker_build_id === "string" ? raw.worker_build_id : null,
  };
}

export async function fetchWnbaFairLines(params?: {
  gameDate?: string;
  modelVersion?: string;
  daysAhead?: number;
}): Promise<WnbaFairLinesResponse> {
  const base = env.MODEL_SERVICE_URL;
  const fallbackDate =
    params?.gameDate ?? new Date().toISOString().slice(0, 10);

  if (!base) {
    return {
      gameDate: fallbackDate,
      modelVersion: "",
      workerBuildId: "",
      count: 0,
      lines: [],
      slateStatus: "misconfigured",
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/wnba/fair-lines`);
  if (params?.gameDate) url.searchParams.set("game_date", params.gameDate);
  if (params?.modelVersion)
    url.searchParams.set("model_version", params.modelVersion);
  if (params?.daysAhead != null)
    url.searchParams.set("days_ahead", String(params.daysAhead));

  try {
    const response = await upstreamFetch(url.toString(), {
      cache: "no-store",
      timeoutMs: UPSTREAM_TIMEOUT_MS.board,
      headers: {
        accept: "application/json",
        ...(env.INTERNAL_API_SECRET
          ? { "x-kosedge-secret": env.INTERNAL_API_SECRET }
          : {}),
      },
    });
    if (!response.ok) {
      return {
        gameDate: fallbackDate,
        modelVersion: "",
        workerBuildId: "",
        count: 0,
        lines: [],
        slateStatus: "upstream_error",
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as {
      game_date?: string;
      model_version?: string;
      worker_build_id?: string;
      count?: number;
      lines?: Record<string, unknown>[];
      slate_status?: string;
      message?: string;
      phase?: string;
    };
    const modelVersion = String(payload.model_version ?? "");
    const lines = (payload.lines ?? []).map((row) =>
      normalizeFairLine(row, modelVersion),
    );
    return {
      gameDate: String(payload.game_date ?? fallbackDate),
      modelVersion,
      workerBuildId: String(payload.worker_build_id ?? ""),
      count: lines.length,
      lines,
      slateStatus: String(payload.slate_status ?? "ok"),
      message: payload.message,
      phase: payload.phase,
    };
  } catch {
    return {
      gameDate: fallbackDate,
      modelVersion: "",
      workerBuildId: "",
      count: 0,
      lines: [],
      slateStatus: "upstream_unreachable",
      error: "Model service unreachable.",
    };
  }
}
