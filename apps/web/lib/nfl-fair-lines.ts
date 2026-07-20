import "server-only";
import { env } from "@/lib/config/env";

export type NflFairLineRow = {
  gameId: string;
  season: number;
  startTime: string | null;
  gameDate: string | null;
  homeTeam: string;
  awayTeam: string;
  homeAbbr: string;
  awayAbbr: string;
  homeWinProb: number | null;
  awayWinProb: number | null;
  spreadHome: number | null;
  totalMean: number | null;
  fairHomeMl: number | null;
  fairAwayMl: number | null;
  modelVersion: string;
  simulationCount: number | null;
  projectionCreatedAt: string | null;
  marketHomeMl: number | null;
  marketAwayMl: number | null;
  marketTotal: number | null;
  marketSpreadHome: number | null;
  marketHomeProbNoVig: number | null;
  mlEdgeProb: number | null;
  totalEdge: number | null;
  spreadEdge: number | null;
  marketJoined: boolean;
};

export type NflFairLinesResponse = {
  season: number;
  modelVersion: string;
  count: number;
  lines: NflFairLineRow[];
  window: { daysAhead: number; includePastDays: number };
  diagnostics: {
    oddsFeedStatus: string;
    oddsFeedError: string | null;
    oddsEventsSeen: number;
    marketJoinedCount: number;
    bookmakers: string[];
    kosedgeOnly: boolean;
  };
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

function toNumber(value: unknown, fallback = 0): number {
  return toNumberOrNull(value) ?? fallback;
}

function toIsoOrNull(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (value instanceof Date) return value.toISOString();
  return null;
}

function normalizeFairLine(raw: Record<string, unknown>): NflFairLineRow {
  return {
    gameId: String(raw.game_id ?? ""),
    season: toNumber(raw.season),
    startTime: toIsoOrNull(raw.start_time),
    gameDate: toIsoOrNull(raw.game_date),
    homeTeam: String(raw.home_team ?? "Home"),
    awayTeam: String(raw.away_team ?? "Away"),
    homeAbbr: String(raw.home_abbr ?? "—"),
    awayAbbr: String(raw.away_abbr ?? "—"),
    homeWinProb: toNumberOrNull(raw.home_win_prob),
    awayWinProb: toNumberOrNull(raw.away_win_prob),
    spreadHome: toNumberOrNull(raw.spread_home),
    totalMean: toNumberOrNull(raw.total_mean),
    fairHomeMl: toNumberOrNull(raw.fair_home_ml),
    fairAwayMl: toNumberOrNull(raw.fair_away_ml),
    modelVersion: String(raw.model_version ?? ""),
    simulationCount: toNumberOrNull(raw.simulation_count),
    projectionCreatedAt: toIsoOrNull(raw.projection_created_at),
    marketHomeMl: toNumberOrNull(raw.market_home_ml),
    marketAwayMl: toNumberOrNull(raw.market_away_ml),
    marketTotal: toNumberOrNull(raw.market_total),
    marketSpreadHome: toNumberOrNull(raw.market_spread_home),
    marketHomeProbNoVig: toNumberOrNull(raw.market_home_prob_no_vig),
    mlEdgeProb: toNumberOrNull(raw.ml_edge_prob),
    totalEdge: toNumberOrNull(raw.total_edge),
    spreadEdge: toNumberOrNull(raw.spread_edge),
    marketJoined: Boolean(raw.market_joined),
  };
}

export async function fetchNflFairLines(params: {
  season: number;
  daysAhead?: number;
  includePastDays?: number;
  modelVersion?: string;
}): Promise<NflFairLinesResponse> {
  const base = env.MODEL_SERVICE_URL;
  const emptyDiagnostics = {
    oddsFeedStatus: "unknown",
    oddsFeedError: null as string | null,
    oddsEventsSeen: 0,
    marketJoinedCount: 0,
    bookmakers: [] as string[],
    kosedgeOnly: true,
  };

  if (!base) {
    return {
      season: params.season,
      modelVersion: "",
      count: 0,
      lines: [],
      window: {
        daysAhead: params.daysAhead ?? 14,
        includePastDays: params.includePastDays ?? 0,
      },
      diagnostics: emptyDiagnostics,
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/nfl/fair-lines`);
  url.searchParams.set("season", String(params.season));
  url.searchParams.set("days_ahead", String(params.daysAhead ?? 14));
  url.searchParams.set("include_past_days", String(params.includePastDays ?? 0));
  if (params.modelVersion) {
    url.searchParams.set("model_version", params.modelVersion);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
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
      return {
        season: params.season,
        modelVersion: "",
        count: 0,
        lines: [],
        window: {
          daysAhead: params.daysAhead ?? 14,
          includePastDays: params.includePastDays ?? 0,
        },
        diagnostics: emptyDiagnostics,
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as {
      season?: number;
      model_version?: string;
      count?: number;
      lines?: Array<Record<string, unknown>>;
      window?: { days_ahead?: number; include_past_days?: number };
      diagnostics?: {
        odds_feed_status?: string;
        odds_feed_error?: string | null;
        odds_events_seen?: number;
        market_joined_count?: number;
        bookmakers?: string[];
        kosedge_only?: boolean;
      };
    };
    const lines = Array.isArray(payload.lines) ? payload.lines.map(normalizeFairLine) : [];
    return {
      season: typeof payload.season === "number" ? payload.season : params.season,
      modelVersion: String(payload.model_version ?? ""),
      count: typeof payload.count === "number" ? payload.count : lines.length,
      lines,
      window: {
        daysAhead: payload.window?.days_ahead ?? params.daysAhead ?? 14,
        includePastDays: payload.window?.include_past_days ?? params.includePastDays ?? 0,
      },
      diagnostics: {
        oddsFeedStatus: String(payload.diagnostics?.odds_feed_status ?? "unknown"),
        oddsFeedError:
          typeof payload.diagnostics?.odds_feed_error === "string"
            ? payload.diagnostics.odds_feed_error
            : null,
        oddsEventsSeen: toNumber(payload.diagnostics?.odds_events_seen),
        marketJoinedCount: toNumber(payload.diagnostics?.market_joined_count),
        bookmakers: Array.isArray(payload.diagnostics?.bookmakers)
          ? payload.diagnostics.bookmakers.map(String)
          : [],
        kosedgeOnly: Boolean(payload.diagnostics?.kosedge_only ?? lines.every((line) => !line.marketJoined)),
      },
    };
  } catch {
    return {
      season: params.season,
      modelVersion: "",
      count: 0,
      lines: [],
      window: {
        daysAhead: params.daysAhead ?? 14,
        includePastDays: params.includePastDays ?? 0,
      },
      diagnostics: emptyDiagnostics,
      error: "Unable to reach model service.",
    };
  } finally {
    clearTimeout(timeout);
  }
}

export function formatAmericanOdds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

export function formatSpread(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded.toFixed(2)}` : rounded.toFixed(2);
}

export function formatTotal(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(1);
}

export function formatWinProb(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatKickoff(value: string | null): string {
  if (!value) return "TBD";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "TBD";
  return date.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export function edgeToneClass(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "text-kos-text/55";
  if (value >= 0.02) return "text-edge-green";
  if (value <= -0.02) return "text-rose-300";
  return "text-kos-text/70";
}
