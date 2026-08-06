import {
  formatAmericanOdds,
  formatTotal,
  type MlbFairLineRow,
} from "@/lib/mlb-fair-lines-format";

export type MlbDeskMarketType = "all" | "ml" | "total" | "run_line";

export type MlbDeskEdgeRow = {
  id: string;
  marketType: Exclude<MlbDeskMarketType, "all">;
  matchup: string;
  detail: string;
  kosedgeLine: string;
  marketLine: string;
  edge: number;
  edgeDisplay: string;
  side: string;
  qualityScore: number | null;
  stakeFraction: number | null;
  source: "edges-today" | "fair-lines";
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

function formatEdgeProb(value: number): string {
  const pp = value * 100;
  return `${pp > 0 ? "+" : ""}${pp.toFixed(1)}pp`;
}

export function formatQuality(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(1);
}

export function formatStakeFraction(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

/** Build desk rows from /mlb/edges/today payload. */
export function deskEdgesFromTodayRow(
  raw: Record<string, unknown>,
  opts: { minProbEdge: number; minLineEdge: number; minQuality: number },
): MlbDeskEdgeRow[] {
  const quality = toNumberOrNull(raw.quality_score);
  if (quality !== null && quality < opts.minQuality) return [];

  const home = String(raw.home_team ?? "Home");
  const away = String(raw.away_team ?? "Away");
  const matchup = `${away} @ ${home}`;
  const gameId = String(raw.game_id ?? matchup);
  const stake = toNumberOrNull(raw.recommended_stake_fraction);
  const out: MlbDeskEdgeRow[] = [];

  const mlEdge = toNumberOrNull(raw.ml_edge_prob);
  if (mlEdge !== null && Math.abs(mlEdge) >= opts.minProbEdge) {
    const homeSide = mlEdge >= 0;
    const fairHome = toNumberOrNull(raw.fair_home_ml);
    const fairAway =
      fairHome === null || fairHome === 0
        ? null
        : fairHome > 0
          ? -fairHome
          : Math.abs(fairHome);
    out.push({
      id: `${gameId}-ml`,
      marketType: "ml",
      matchup,
      detail: "Moneyline",
      kosedgeLine: formatAmericanOdds(homeSide ? fairHome : fairAway),
      marketLine: formatAmericanOdds(
        homeSide
          ? toNumberOrNull(raw.market_home_ml)
          : toNumberOrNull(raw.market_away_ml),
      ),
      edge: mlEdge,
      edgeDisplay: formatEdgeProb(mlEdge),
      side: homeSide ? "Home" : "Away",
      qualityScore: quality,
      stakeFraction: stake,
      source: "edges-today",
    });
  }

  const totalEdge = toNumberOrNull(raw.total_edge);
  if (totalEdge !== null && Math.abs(totalEdge) >= opts.minLineEdge) {
    const over = totalEdge > 0;
    out.push({
      id: `${gameId}-total`,
      marketType: "total",
      matchup,
      detail: "Total runs",
      kosedgeLine: formatTotal(toNumberOrNull(raw.fair_total)),
      marketLine: formatTotal(toNumberOrNull(raw.market_total)),
      edge: totalEdge,
      edgeDisplay: `${totalEdge > 0 ? "+" : ""}${totalEdge.toFixed(1)} runs`,
      side: over ? "Over" : "Under",
      qualityScore: quality,
      stakeFraction: stake,
      source: "edges-today",
    });
  }

  return out;
}

/** Optional run-line candidates from fair-lines when cover prob is extreme. */
export function deskRunLineFromFairLine(
  row: MlbFairLineRow,
  opts: { minCoverLean: number },
): MlbDeskEdgeRow | null {
  const cover = row.runLineCoverProbHome;
  if (cover === null) return null;
  const lean = cover - 0.5;
  if (Math.abs(lean) < opts.minCoverLean) return null;
  const homeSide = lean >= 0;
  return {
    id: `${row.gameId}-run-line`,
    marketType: "run_line",
    matchup: `${row.awayTeam} @ ${row.homeTeam}`,
    detail: "Run line (−1.5 / +1.5)",
    kosedgeLine:
      row.fairSpreadHome !== null ? row.fairSpreadHome.toFixed(1) : "−1.5",
    marketLine: "—",
    edge: lean,
    edgeDisplay: formatEdgeProb(lean),
    side: homeSide ? "Home −1.5" : "Away +1.5",
    qualityScore: null,
    stakeFraction: null,
    source: "fair-lines",
  };
}
