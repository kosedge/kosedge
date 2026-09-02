import "server-only";
import { env } from "@/lib/config/env";
import {
  fetchNflFairLines,
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";
import {
  fetchNflPropsBoard,
  formatConfidence,
  formatEdgeProb,
  formatPropNumber,
  propMarketLabel,
  type NflPropBoardRow,
} from "@/lib/nfl-props-board";
import { lookupCanonicalNflGameForTeam } from "@/lib/nfl-canonical-schedule";
import { resolveNflKickoffIso } from "@/lib/nfl-schedule-kickoff";
import {
  edgesMayShowPropRows,
  nflPropsSurfaceState,
  type NflPropsSurfaceState,
} from "@/lib/nfl-props-surface";

export type DeskMarketType = "all" | "ml" | "spread" | "total" | "props";

export type DeskEdgeRow = {
  id: string;
  marketType: Exclude<DeskMarketType, "all">;
  matchupOrPlayer: string;
  detail: string;
  kosedgeLine: string;
  marketLine: string;
  edge: number;
  edgeDisplay: string;
  side: string;
  confidence: number | null;
  kickoff: string | null;
  source: "fair-lines" | "edges-today" | "props";
};

export type NflEdgesDeskResponse = {
  season: number;
  week: number;
  count: number;
  rows: DeskEdgeRow[];
  filters: {
    market: DeskMarketType;
    minProbEdge: number;
    minLineEdge: number;
    minConfidence: number;
  };
  propsSurface: NflPropsSurfaceState;
  diagnostics: {
    gameCandidates: number;
    propCandidates: number;
    fairLinesError?: string;
    edgesTodayError?: string;
    propsError?: string;
  };
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

/** Pure: turn a fair-lines row into zero or more actionable desk edges. */
export function deskEdgesFromFairLine(
  row: NflFairLineRow,
  opts: { minProbEdge: number; minLineEdge: number },
): DeskEdgeRow[] {
  const { minProbEdge, minLineEdge } = opts;
  if (!row.marketJoined) return [];
  const matchup = `${row.awayAbbr} @ ${row.homeAbbr}`;
  const kickoff = resolveNflKickoffIso({
    gameId: row.gameId,
    season: row.season,
    week: row.week,
    awayAbbr: row.awayAbbr,
    homeAbbr: row.homeAbbr,
    startTime: row.startTime,
    gameDate: row.gameDate,
  });
  const out: DeskEdgeRow[] = [];

  if (row.mlEdgeProb !== null && Math.abs(row.mlEdgeProb) >= minProbEdge) {
    const homeSide = row.mlEdgeProb >= 0;
    out.push({
      id: `${row.gameId}-ml`,
      marketType: "ml",
      matchupOrPlayer: matchup,
      detail: "Moneyline",
      kosedgeLine: formatAmericanOdds(
        homeSide ? row.fairHomeMl : row.fairAwayMl,
      ),
      marketLine: formatAmericanOdds(
        homeSide ? row.marketHomeMl : row.marketAwayMl,
      ),
      edge: row.mlEdgeProb,
      edgeDisplay: formatEdgeProb(row.mlEdgeProb),
      side: homeSide ? "Home" : "Away",
      confidence: null,
      kickoff,
      source: "fair-lines",
    });
  }

  if (row.spreadEdge !== null && Math.abs(row.spreadEdge) >= minLineEdge) {
    // Negative spreadEdge => Kosedge home line more favored than market → lean Home
    const leanHome = row.spreadEdge < 0;
    out.push({
      id: `${row.gameId}-spread`,
      marketType: "spread",
      matchupOrPlayer: matchup,
      detail: "Spread",
      kosedgeLine: formatSpread(row.spreadHome),
      marketLine: formatSpread(row.marketSpreadHome),
      edge: row.spreadEdge,
      edgeDisplay: `${row.spreadEdge > 0 ? "+" : ""}${row.spreadEdge.toFixed(1)} pts`,
      side: leanHome ? "Home" : "Away",
      confidence: null,
      kickoff,
      source: "fair-lines",
    });
  }

  if (row.totalEdge !== null && Math.abs(row.totalEdge) >= minLineEdge) {
    const over = row.totalEdge > 0;
    out.push({
      id: `${row.gameId}-total`,
      marketType: "total",
      matchupOrPlayer: matchup,
      detail: "Total",
      kosedgeLine: formatTotal(row.totalMean),
      marketLine: formatTotal(row.marketTotal),
      edge: row.totalEdge,
      edgeDisplay: `${row.totalEdge > 0 ? "+" : ""}${row.totalEdge.toFixed(1)} pts`,
      side: over ? "Over" : "Under",
      confidence: null,
      kickoff,
      source: "fair-lines",
    });
  }

  return out;
}

/** Pure: prop board row → best-side desk edge when market joined and above threshold. */
export function deskEdgeFromPropRow(
  row: NflPropBoardRow,
  opts: { minProbEdge: number; minConfidence: number },
): DeskEdgeRow | null {
  const { minProbEdge, minConfidence } = opts;
  if (!row.marketJoined) return null;
  if (row.confidence !== null && row.confidence < minConfidence) return null;

  const over = row.edgeOver;
  const under = row.edgeUnder;
  // Lean follows positive probability edge only (never abs-tie → Over).
  // Do not fall back to modelMean − line yards — that mixes units into formatEdgeProb.
  const overPos = over !== null && over > 0 ? over : -1;
  const underPos = under !== null && under > 0 ? under : -1;
  if (overPos < minProbEdge && underPos < minProbEdge) return null;

  const takeOver = overPos >= underPos && overPos > 0;
  const edge = takeOver ? (over ?? 0) : (under ?? 0);
  if (edge <= 0 || Math.abs(edge) < minProbEdge) return null;

  const kickoff =
    lookupCanonicalNflGameForTeam({
      week: row.week,
      teamAbbr: row.team,
    })?.kickoff_utc ?? null;

  return {
    id: `${row.playerId ?? row.playerName}-${row.marketKey}-${row.week}`,
    marketType: "props",
    matchupOrPlayer: row.playerName,
    detail: `${propMarketLabel(row.marketKey)} · ${row.team}`,
    kosedgeLine: formatPropNumber(row.modelMean),
    marketLine: formatPropNumber(row.line),
    edge,
    edgeDisplay: formatEdgeProb(edge),
    side: takeOver ? "Over" : "Under",
    confidence: row.confidence,
    kickoff,
    source: "props",
  };
}

function normalizeEdgesTodayRow(
  raw: Record<string, unknown>,
  minProbEdge: number,
): DeskEdgeRow | null {
  const mlEdge = toNumberOrNull(raw.ml_edge_prob);
  if (mlEdge === null || Math.abs(mlEdge) < minProbEdge) return null;
  const home = String(raw.home_team ?? "Home");
  const away = String(raw.away_team ?? "Away");
  const homeSide = mlEdge >= 0;
  return {
    id: `${String(raw.game_id ?? "game")}-today-ml`,
    marketType: "ml",
    matchupOrPlayer: `${away} @ ${home}`,
    detail: "Moneyline (today)",
    kosedgeLine: formatAmericanOdds(
      toNumberOrNull(homeSide ? raw.fair_home_ml : raw.fair_away_ml),
    ),
    marketLine: formatAmericanOdds(
      toNumberOrNull(homeSide ? raw.market_home_ml : raw.market_away_ml),
    ),
    edge: mlEdge,
    edgeDisplay: formatEdgeProb(mlEdge),
    side: homeSide ? "Home" : "Away",
    confidence: toNumberOrNull(raw.confidence_score),
    kickoff: typeof raw.start_time === "string" ? raw.start_time : null,
    source: "edges-today",
  };
}

async function fetchNflEdgesToday(params: {
  minMlEdgeProb?: number;
  minConfidenceScore?: number;
}): Promise<{ rows: DeskEdgeRow[]; error?: string }> {
  const base = env.MODEL_SERVICE_URL;
  if (!base) return { rows: [], error: "MODEL_SERVICE_URL is not configured." };

  const url = new URL(`${base.replace(/\/+$/, "")}/nfl/edges/today`);
  if (params.minMlEdgeProb != null) {
    url.searchParams.set("min_ml_edge_prob", String(params.minMlEdgeProb));
  }
  if (params.minConfidenceScore != null) {
    url.searchParams.set(
      "min_confidence_score",
      String(params.minConfidenceScore),
    );
  }

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
      return { rows: [], error: `Model service returned ${response.status}.` };
    }
    const payload = (await response.json()) as {
      edges?: Array<Record<string, unknown>>;
    };
    const edges = Array.isArray(payload.edges) ? payload.edges : [];
    const rows = edges
      .map((raw) => normalizeEdgesTodayRow(raw, params.minMlEdgeProb ?? 0.02))
      .filter((row): row is DeskEdgeRow => row !== null);
    return { rows };
  } catch {
    return { rows: [], error: "Unable to reach model service." };
  } finally {
    clearTimeout(timeout);
  }
}

export function filterDeskRows(
  rows: DeskEdgeRow[],
  market: DeskMarketType,
): DeskEdgeRow[] {
  const filtered =
    market === "all" ? rows : rows.filter((row) => row.marketType === market);
  return [...filtered].sort((a, b) => Math.abs(b.edge) - Math.abs(a.edge));
}

export async function fetchNflEdgesDesk(params: {
  season: number;
  week: number;
  market?: DeskMarketType;
  minProbEdge?: number;
  minLineEdge?: number;
  minConfidence?: number;
  daysAhead?: number;
  propLimit?: number;
}): Promise<NflEdgesDeskResponse> {
  const market = params.market ?? "all";
  const minProbEdge = params.minProbEdge ?? 0.02;
  const minLineEdge = params.minLineEdge ?? 1.0;
  const minConfidence = params.minConfidence ?? 0;
  const daysAhead = params.daysAhead ?? 120;

  const [fairBoard, todayBoard, propsBoard] = await Promise.all([
    fetchNflFairLines({ season: params.season, daysAhead }),
    fetchNflEdgesToday({
      minMlEdgeProb: minProbEdge,
      minConfidenceScore: minConfidence > 0 ? minConfidence : undefined,
    }),
    fetchNflPropsBoard({
      season: params.season,
      week: params.week,
      minAbsEdge: minProbEdge,
      minConfidence: minConfidence > 0 ? minConfidence : undefined,
      limit: params.propLimit ?? 500,
    }),
  ]);

  // Desk week is authoritative — do not mix forward-week fair-lines into W1.
  const weekLines = fairBoard.lines.filter(
    (line) => line.week == null || line.week === params.week,
  );
  const fairEdges = weekLines.flatMap((line) =>
    deskEdgesFromFairLine(line, { minProbEdge, minLineEdge }),
  );
  const todayIds = new Set(
    todayBoard.rows.map((row) => row.id.replace("-today-ml", "-ml")),
  );
  const mergedGame = [
    ...fairEdges,
    ...todayBoard.rows.filter(
      (row) => !todayIds.has(row.id.replace("-today-ml", "-ml")),
    ),
  ];

  const propSurface = nflPropsSurfaceState(propsBoard);
  const propEdges = edgesMayShowPropRows(propSurface)
    ? propsBoard.rows
        .map((row) => deskEdgeFromPropRow(row, { minProbEdge, minConfidence }))
        .filter((row): row is DeskEdgeRow => row !== null)
    : [];

  const allRows = filterDeskRows([...mergedGame, ...propEdges], market);

  return {
    season: params.season,
    week: params.week,
    count: allRows.length,
    rows: allRows,
    filters: { market, minProbEdge, minLineEdge, minConfidence },
    propsSurface: propSurface,
    diagnostics: {
      gameCandidates: mergedGame.length,
      propCandidates: propEdges.length,
      fairLinesError: fairBoard.error,
      edgesTodayError: todayBoard.error,
      propsError: propsBoard.error,
    },
  };
}

export {
  formatAmericanOdds,
  formatConfidence,
  formatEdgeProb,
  formatKickoff,
  formatPropNumber,
  formatSpread,
  formatTotal,
};
