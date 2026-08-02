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
import { UPSTREAM_TIMEOUT_MS, upstreamFetch } from "@/lib/upstream-fetch";

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

function firstNumber(
  ...candidates: Array<unknown>
): number | null {
  for (const c of candidates) {
    const n = toNumberOrNull(c);
    if (n !== null) return n;
  }
  return null;
}

function normalizeFairLine(
  raw: Record<string, unknown>,
  modelVersion: string,
): MlbFairLineRow {
  // Handicap = KEI. fair_fg_* is handicap alias for one release.
  const handicapHomeMl = firstNumber(
    raw.handicap_fair_fg_home_ml,
    raw.fair_fg_home_ml,
  );
  const handicapAwayMl =
    firstNumber(raw.handicap_fair_fg_away_ml) ??
    fairAwayFromHome(handicapHomeMl);
  const handicapHomeWinProb = firstNumber(
    raw.handicap_fg_home_win_prob,
    raw.fg_home_win_prob,
  );
  const handicapTotal = firstNumber(
    raw.handicap_fair_fg_total,
    raw.fair_fg_total,
  );
  const handicapTotalMean = firstNumber(
    raw.handicap_fg_total_mean,
    raw.fg_total_mean,
  );
  const handicapSpreadHome = firstNumber(
    raw.handicap_fair_fg_spread_home,
    raw.fair_fg_spread_home,
  );

  // Model = pure sim; identity fallback to handicap when absent.
  const modelHomeMl = firstNumber(
    raw.model_fair_fg_home_ml,
    handicapHomeMl,
  );
  const modelAwayMl =
    firstNumber(raw.model_fair_fg_away_ml) ?? fairAwayFromHome(modelHomeMl);
  const modelHomeWinProb = firstNumber(
    raw.model_fg_home_win_prob,
    handicapHomeWinProb,
  );
  const modelTotal = firstNumber(raw.model_fair_fg_total, handicapTotal);
  const modelTotalMean = firstNumber(
    raw.model_fg_total_mean,
    handicapTotalMean,
  );
  const modelSpreadHome = firstNumber(
    raw.model_fair_fg_spread_home,
    handicapSpreadHome,
  );

  return {
    gameId: String(raw.game_id ?? ""),
    gameDate: toIsoOrNull(raw.game_date),
    startTime: toIsoOrNull(raw.start_time),
    homeTeam: String(raw.home_team ?? "Home"),
    awayTeam: String(raw.away_team ?? "Away"),
    // Legacy aliases = handicap
    homeWinProb: handicapHomeWinProb,
    fairHomeMl: handicapHomeMl,
    fairAwayMl: handicapAwayMl,
    totalMean: handicapTotalMean,
    fairTotal: handicapTotal,
    fairSpreadHome: handicapSpreadHome,
    runLineCoverProbHome: toNumberOrNull(raw.fg_home_cover_prob_run_line),
    marginMean: toNumberOrNull(raw.fg_margin_mean),
    projectedAt: toIsoOrNull(raw.projected_at),
    modelVersion,
    handicapHomeWinProb,
    handicapHomeMl,
    handicapAwayMl,
    handicapTotal,
    handicapTotalMean,
    handicapSpreadHome,
    modelHomeWinProb,
    modelHomeMl,
    modelAwayMl,
    modelTotal,
    modelTotalMean,
    modelSpreadHome,
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
  }
}
