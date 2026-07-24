import "server-only";
import { env } from "@/lib/config/env";

export type NflPropBoardRow = {
  season: number;
  week: number;
  modelVersion: string;
  gameId: string | null;
  playerId: string | null;
  playerUid: string | null;
  playerName: string;
  team: string;
  marketKey: string;
  line: number | null;
  modelMean: number | null;
  modelStd: number | null;
  modelFloor: number | null;
  modelMedian: number | null;
  modelCeiling: number | null;
  overProb: number | null;
  underProb: number | null;
  fairOverPrice: number | null;
  fairUnderPrice: number | null;
  marketOverPrice: number | null;
  marketUnderPrice: number | null;
  edgeOver: number | null;
  edgeUnder: number | null;
  confidence: number | null;
  updatedAt: string | null;
  marketJoined: boolean;
  tag: "PLAY" | "WATCH" | "LEAN" | "PASS" | null;
  tagSide: string | null;
  tagAction: string | null;
  sizeDown: boolean;
  stakeEligible: boolean;
  projectionSource: "box_score" | "baseline" | null;
  zOver: number | null;
};

export type NflPropsBoardResponse = {
  count: number;
  rows: NflPropBoardRow[];
  diagnostics: {
    marketJoinedCount: number;
    kosedgeOnly: boolean;
    playCount?: number;
    watchCount?: number;
    leanCount?: number;
    boxScoreSourcedCount?: number;
  };
  error?: string;
};

export const PROP_MARKET_LABELS: Record<string, string> = {
  pass_yds: "Pass Yards",
  rush_yds: "Rush Yards",
  rec_yds: "Receiving Yards",
  receptions: "Receptions",
  pass_tds: "Pass TDs",
  rush_tds: "Rush TDs",
  rec_tds: "Rec TDs",
  anytime_td: "Anytime TD",
  completions: "Completions",
  attempts: "Pass Attempts",
  longest_reception: "Longest Reception",
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

function normalizePropRow(raw: Record<string, unknown>): NflPropBoardRow {
  const marketOver = toNumberOrNull(raw.market_over_price);
  const marketUnder = toNumberOrNull(raw.market_under_price);
  const diagnostics =
    raw.diagnostics && typeof raw.diagnostics === "object"
      ? (raw.diagnostics as Record<string, unknown>)
      : {};
  const tagRaw =
    typeof diagnostics.tag === "string" ? diagnostics.tag.toUpperCase() : null;
  const tag =
    tagRaw === "PLAY" ||
    tagRaw === "WATCH" ||
    tagRaw === "LEAN" ||
    tagRaw === "PASS"
      ? tagRaw
      : null;
  const sourceRaw =
    typeof diagnostics.projection_source === "string"
      ? diagnostics.projection_source
      : null;
  return {
    season: toNumber(raw.season),
    week: toNumber(raw.week),
    modelVersion: String(raw.model_version ?? ""),
    gameId: raw.game_id != null ? String(raw.game_id) : null,
    playerId: raw.player_id != null ? String(raw.player_id) : null,
    playerUid: typeof raw.player_uid === "string" ? raw.player_uid : null,
    playerName: String(raw.player_name ?? "Unknown player"),
    team: String(raw.team ?? "—"),
    marketKey: String(raw.market_key ?? "—"),
    line: toNumberOrNull(raw.line),
    modelMean: toNumberOrNull(raw.model_mean),
    modelStd: toNumberOrNull(raw.model_std),
    modelFloor: toNumberOrNull(raw.model_floor),
    modelMedian: toNumberOrNull(raw.model_median),
    modelCeiling: toNumberOrNull(raw.model_ceiling),
    overProb: toNumberOrNull(raw.over_prob),
    underProb: toNumberOrNull(raw.under_prob),
    fairOverPrice: toNumberOrNull(raw.fair_over_price),
    fairUnderPrice: toNumberOrNull(raw.fair_under_price),
    marketOverPrice: marketOver,
    marketUnderPrice: marketUnder,
    edgeOver: toNumberOrNull(raw.edge_over),
    edgeUnder: toNumberOrNull(raw.edge_under),
    confidence: toNumberOrNull(raw.confidence),
    updatedAt: toIsoOrNull(raw.updated_at),
    marketJoined: marketOver !== null || marketUnder !== null,
    tag,
    tagSide:
      typeof diagnostics.tag_side === "string" ? diagnostics.tag_side : null,
    tagAction:
      typeof diagnostics.tag_action === "string"
        ? diagnostics.tag_action
        : null,
    sizeDown: Boolean(diagnostics.size_down),
    stakeEligible: Boolean(diagnostics.stake_eligible ?? tagRaw === "PLAY"),
    projectionSource:
      sourceRaw === "box_score" || sourceRaw === "baseline" ? sourceRaw : null,
    zOver: toNumberOrNull(diagnostics.z_over),
  };
}

export async function fetchNflPropsBoard(params: {
  season: number;
  week: number;
  modelVersion?: string;
  marketKey?: string;
  team?: string;
  tag?: string;
  minConfidence?: number;
  minAbsEdge?: number;
  limit?: number;
}): Promise<NflPropsBoardResponse> {
  const base = env.MODEL_SERVICE_URL;
  const emptyDiagnostics = { marketJoinedCount: 0, kosedgeOnly: true };

  if (!base) {
    return {
      count: 0,
      rows: [],
      diagnostics: emptyDiagnostics,
      error: "MODEL_SERVICE_URL is not configured.",
    };
  }

  const url = new URL(`${base.replace(/\/+$/, "")}/nfl/props/board`);
  url.searchParams.set("season", String(params.season));
  url.searchParams.set("week", String(params.week));
  url.searchParams.set("model_version", params.modelVersion ?? "nfl-player-v1");
  url.searchParams.set("min_confidence", String(params.minConfidence ?? 0));
  url.searchParams.set("min_abs_edge", String(params.minAbsEdge ?? 0));
  url.searchParams.set("limit", String(params.limit ?? 250));
  if (params.marketKey) url.searchParams.set("market_key", params.marketKey);
  if (params.team) url.searchParams.set("team", params.team.toUpperCase());
  if (params.tag) url.searchParams.set("tag", params.tag.toUpperCase());

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
      return {
        count: 0,
        rows: [],
        diagnostics: emptyDiagnostics,
        error: `Model service returned ${response.status}.`,
      };
    }
    const payload = (await response.json()) as {
      count?: number;
      rows?: Array<Record<string, unknown>>;
      diagnostics?: {
        market_joined_count?: number;
        kosedge_only?: boolean;
        play_count?: number;
        watch_count?: number;
        lean_count?: number;
        box_score_sourced_count?: number;
      };
    };
    const rows = Array.isArray(payload.rows)
      ? payload.rows.map(normalizePropRow)
      : [];
    const marketJoinedCount =
      typeof payload.diagnostics?.market_joined_count === "number"
        ? payload.diagnostics.market_joined_count
        : rows.filter((row) => row.marketJoined).length;
    return {
      count: typeof payload.count === "number" ? payload.count : rows.length,
      rows,
      diagnostics: {
        marketJoinedCount,
        kosedgeOnly: Boolean(
          payload.diagnostics?.kosedge_only ??
          (rows.length > 0 && marketJoinedCount === 0),
        ),
        playCount: payload.diagnostics?.play_count,
        watchCount:
          payload.diagnostics?.watch_count ?? payload.diagnostics?.lean_count,
        leanCount: payload.diagnostics?.lean_count,
        boxScoreSourcedCount: payload.diagnostics?.box_score_sourced_count,
      },
    };
  } catch {
    return {
      count: 0,
      rows: [],
      diagnostics: emptyDiagnostics,
      error: "Unable to reach model service.",
    };
  } finally {
    clearTimeout(timeout);
  }
}

export function propMarketLabel(marketKey: string): string {
  return PROP_MARKET_LABELS[marketKey] ?? marketKey.replace(/_/g, " ");
}

export function formatPropNumber(value: number | null, digits = 1): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

export function formatAmericanOdds(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const rounded = Math.round(value);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

export function formatEdgeProb(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const pct = value * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}pp`;
}

export function formatConfidence(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(0)}%`;
}
