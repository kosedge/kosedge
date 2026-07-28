import "server-only";
import { env } from "@/lib/config/env";
import {
  type MlbFairLineRow,
  formatAmericanOdds,
  formatKickoff,
  formatRunLine,
  formatTotal,
  formatWinProb,
} from "@/lib/mlb-fair-lines-format";

export type { MlbFairLineRow };
export {
  formatAmericanOdds,
  formatKickoff,
  formatRunLine,
  formatTotal,
  formatWinProb,
};

export type MlbFairLinesResponse = {
  gameDate: string;
  modelVersion: string;
  count: number;
  lines: MlbFairLineRow[];
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
): MlbFairLineRow {
  const fairHomeMl = toNumberOrNull(raw.fair_fg_home_ml);
  return {
    gameId: String(raw.game_id ?? ""),
    gameDate: toIsoOrNull(raw.game_date),
    startTime: toIsoOrNull(raw.start_time),
    homeTeam: String(raw.home_team ?? "Home"),
    awayTeam: String(raw.away_team ?? "Away"),
    homeWinProb: toNumberOrNull(raw.fg_home_win_prob),
    fairHomeMl,
    fairAwayMl: fairAwayFromHome(fairHomeMl),
    totalMean: toNumberOrNull(raw.fg_total_mean),
    fairTotal: toNumberOrNull(raw.fair_fg_total),
    fairSpreadHome: toNumberOrNull(raw.fair_fg_spread_home),
    runLineCoverProbHome: toNumberOrNull(raw.fg_home_cover_prob_run_line),
    marginMean: toNumberOrNull(raw.fg_margin_mean),
    projectedAt: toIsoOrNull(raw.projected_at),
    modelVersion,
  };
}

export async function fetchMlbFairLines(params?: {
  gameDate?: string;
  modelVersion?: string;
}): Promise<MlbFairLinesResponse> {
  const base = env.MODEL_SERVICE_URL;
  const fallbackDate =
    params?.gameDate ?? new Date().toISOString().slice(0, 10);

  if (!base) {
    return {
      gameDate: fallbackDate,
      modelVersion: "",
      count: 0,
      lines: [],
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/mlb/fair-lines`);
  if (params?.gameDate) url.searchParams.set("game_date", params.gameDate);
  if (params?.modelVersion)
    url.searchParams.set("model_version", params.modelVersion);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
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
      return {
        gameDate: fallbackDate,
        modelVersion: "",
        count: 0,
        lines: [],
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as {
      game_date?: string;
      model_version?: string;
      count?: number;
      lines?: Array<Record<string, unknown>>;
    };
    const modelVersion = String(payload.model_version ?? "");
    const lines = Array.isArray(payload.lines)
      ? payload.lines.map((row) => normalizeFairLine(row, modelVersion))
      : [];
    return {
      gameDate:
        typeof payload.game_date === "string"
          ? payload.game_date.slice(0, 10)
          : fallbackDate,
      modelVersion,
      count: typeof payload.count === "number" ? payload.count : lines.length,
      lines,
    };
  } catch {
    return {
      gameDate: fallbackDate,
      modelVersion: "",
      count: 0,
      lines: [],
      error: "Unable to reach model service.",
    };
  } finally {
    clearTimeout(timeout);
  }
}
