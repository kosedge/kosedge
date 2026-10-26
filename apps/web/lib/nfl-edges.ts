import "server-only";
import {
  fetchNflFairLines,
  formatAmericanOdds,
  formatKickoff,
  formatSpread,
  formatTotal,
  type NflFairLineRow,
} from "@/lib/nfl-fair-lines";
import {
  formatConfidence,
  formatEdgeProb,
  formatPropNumber,
  propMarketLabel,
  type NflPropBoardRow,
} from "@/lib/nfl-props-board";
import { lookupCanonicalNflGameForTeam } from "@/lib/nfl-canonical-schedule";
import { resolveNflKickoffIso } from "@/lib/nfl-schedule-kickoff";
import {
  NFL_EDGES_PROPS_STATUS,
  nflFairLinesObservedIdentity,
  nflSurfaceProvenanceFromEdgesDesk,
  selectNflEdgesCustomerPaintRows,
  bindNflEdgesToFairLinesCertifiedRun,
  checkNflObservedAgainstCertifiedSlot,
} from "@/lib/nfl-surface-provenance";
import {
  formatSelectedSideLineEdge,
  formatSelectedSideProbEdge,
  pickEdgeMarketLine,
  reconcileHandicapCustomerEdge,
  reconcileMoneylineCustomerEdge,
  reconcileTotalCustomerEdge,
} from "@/lib/edge-board-customer-truth";
import {
  sanitizeNflSpread,
  sanitizeNflTotal,
} from "@/lib/nfl-market-line-hygiene";

export type {
  DeskEdgeRow,
  DeskMarketType,
  NflEdgesDeskResponse,
} from "@/lib/nfl-edges-desk-types";
import type {
  DeskEdgeRow,
  DeskMarketType,
  NflEdgesDeskResponse,
} from "@/lib/nfl-edges-desk-types";

function fairLineDeskConfidence(
  row: NflFairLineRow,
  market: "ml" | "spread" | "total",
): number | null {
  const decision = row.decision;
  if (!decision) return null;
  const perMarket =
    market === "spread"
      ? decision.spread?.modelConfidence?.score
      : market === "total"
        ? decision.total?.modelConfidence?.score
        : null;
  if (perMarket != null && Number.isFinite(perMarket)) return perMarket;
  const rowLevel = decision.modelConfidence?.score;
  return rowLevel != null && Number.isFinite(rowLevel) ? rowLevel : null;
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
    // ML has its own formula (prob pts) — never abs(fairAmerican−marketAmerican).
    const ml = reconcileMoneylineCustomerEdge({
      signedProbEdge: row.mlEdgeProb,
    });
    if (ml.status === "ok" && ml.advantage != null && ml.side != null) {
      const homeSide = ml.side === "Home";
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
        // Positive selected-side magnitude only (customer-truth contract).
        edge: ml.advantage,
        edgeDisplay: formatSelectedSideProbEdge(ml.advantage),
        side: ml.side,
        confidence: fairLineDeskConfidence(row, "ml"),
        kickoff,
        source: "fair-lines",
        linesAsOf: row.oddsCapturedAt?.trim() || null,
      });
    }
  }

  if (row.spreadEdge !== null && Math.abs(row.spreadEdge) >= minLineEdge) {
    // Market painted MUST be the stake/compare line used for spread_edge — not consensus alone.
    const marketForEdge = pickEdgeMarketLine({
      stake: row.stakeSpreadHome,
      dk: row.dkSpreadHome,
      fd: row.fdSpreadHome,
      market: row.marketSpreadHome,
      best: row.bestSpreadHome,
      sanitize: (n) => sanitizeNflSpread(n).value,
    });
    const fair = row.spreadHome ?? row.handicapSpreadHome;
    const reconciled = reconcileHandicapCustomerEdge({
      fairLine: fair,
      marketLine: marketForEdge,
      claimedEdge: row.spreadEdge,
    });
    // Fail closed on Fair/Book/Edge disagreement — no painted edge chrome.
    if (
      reconciled.status === "ok" &&
      reconciled.advantage != null &&
      reconciled.side != null &&
      reconciled.advantage >= minLineEdge
    ) {
      out.push({
        id: `${row.gameId}-spread`,
        marketType: "spread",
        matchupOrPlayer: matchup,
        detail: "Spread",
        kosedgeLine: formatSpread(reconciled.fairLine),
        marketLine: formatSpread(reconciled.marketLine),
        edge: reconciled.advantage,
        edgeDisplay: formatSelectedSideLineEdge(reconciled.advantage, "pts"),
        side: reconciled.side,
        confidence: fairLineDeskConfidence(row, "spread"),
        kickoff,
        source: "fair-lines",
        linesAsOf: row.oddsCapturedAt?.trim() || null,
      });
    }
  }

  if (row.totalEdge !== null && Math.abs(row.totalEdge) >= minLineEdge) {
    // Totals: own formula; market = stake close used for total_edge.
    const marketForEdge = pickEdgeMarketLine({
      stake: row.stakeTotal,
      dk: row.dkTotal,
      fd: row.fdTotal,
      market: row.marketTotal,
      best: row.bestTotal,
      sanitize: (n) => sanitizeNflTotal(n).value,
    });
    const fair = row.totalMean ?? row.handicapTotal;
    const reconciled = reconcileTotalCustomerEdge({
      fairTotal: fair,
      marketTotal: marketForEdge,
      claimedEdge: row.totalEdge,
    });
    if (
      reconciled.status === "ok" &&
      reconciled.advantage != null &&
      reconciled.side != null &&
      reconciled.advantage >= minLineEdge
    ) {
      out.push({
        id: `${row.gameId}-total`,
        marketType: "total",
        matchupOrPlayer: matchup,
        detail: "Total",
        kosedgeLine: formatTotal(reconciled.fairTotal),
        marketLine: formatTotal(reconciled.marketTotal),
        edge: reconciled.advantage,
        edgeDisplay: formatSelectedSideLineEdge(reconciled.advantage, "pts"),
        side: reconciled.side,
        confidence: fairLineDeskConfidence(row, "total"),
        kickoff,
        source: "fair-lines",
        linesAsOf: row.oddsCapturedAt?.trim() || null,
      });
    }
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
  // Lean follows model − line: positive Over edge → Over; positive Under → Under.
  // Never pick Over on a symmetric abs-tie when the model is below the book.
  const overPos = over !== null && over > 0 ? over : -1;
  const underPos = under !== null && under > 0 ? under : -1;
  if (overPos < minProbEdge && underPos < minProbEdge) {
    // Fallback: signed model vs line when edge probs are tied/missing.
    if (
      row.modelMean !== null &&
      row.line !== null &&
      Math.abs(row.modelMean - row.line) >= 1e-9
    ) {
      const takeOver = row.modelMean > row.line;
      const signed =
        takeOver && over !== null
          ? over
          : !takeOver && under !== null
            ? under
            : row.modelMean - row.line;
      const advantage = Math.abs(signed);
      if (advantage < minProbEdge) return null;
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
        edge: advantage,
        edgeDisplay: formatSelectedSideProbEdge(advantage),
        side: takeOver ? "Over" : "Under",
        confidence: row.confidence,
        kickoff,
        source: "props",
        linesAsOf: null,
      };
    }
    return null;
  }

  const takeOver = overPos >= underPos && overPos > 0;
  const edge = takeOver ? (over ?? 0) : (under ?? 0);
  if (edge <= 0 || Math.abs(edge) < minProbEdge) return null;
  const advantage = Math.abs(edge);

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
    edge: advantage,
    edgeDisplay: formatSelectedSideProbEdge(advantage),
    side: takeOver ? "Over" : "Under",
    confidence: row.confidence,
    kickoff,
    source: "props",
    linesAsOf: null,
  };
}

export function filterDeskRows(
  rows: DeskEdgeRow[],
  market: DeskMarketType,
): DeskEdgeRow[] {
  const filtered =
    market === "all" ? rows : rows.filter((row) => row.marketType === market);
  return [...filtered].sort((a, b) => Math.abs(b.edge) - Math.abs(a.edge));
}

/**
 * Pure desk assembly (N-1 / E-2 / X-4). Props and edges-today rows are
 * accepted only so tests can prove they are omitted. Customer `rows` are
 * always filtered through selectNflEdgesCustomerPaintRows.
 */
export function assembleNflEdgesDeskPayload(input: {
  season: number;
  week: number;
  market: DeskMarketType;
  minProbEdge: number;
  minLineEdge: number;
  minConfidence: number;
  fairOddsAsOf: string | null;
  fairBooks?: string[];
  fairLinesError?: string;
  fairEdges?: DeskEdgeRow[];
  todayEdges?: DeskEdgeRow[];
  propEdges?: DeskEdgeRow[];
}): NflEdgesDeskResponse {
  const observed = nflSurfaceProvenanceFromEdgesDesk({
    marketAsOf: input.fairOddsAsOf,
    // Observed identity comes from the Fair Lines leg. Unbound → null.
    // Do not invent or copy a certified-slot placeholder.
    ...nflFairLinesObservedIdentity(),
  });
  const bind = bindNflEdgesToFairLinesCertifiedRun({
    runId: observed.runId,
    sha256: observed.sha256,
  });
  const slot = checkNflObservedAgainstCertifiedSlot({ observed });
  const candidates = [
    ...(input.fairEdges ?? []),
    ...(input.todayEdges ?? []),
    ...(input.propEdges ?? []),
  ];
  const painted = selectNflEdgesCustomerPaintRows(candidates, {
    observed,
    bindOk: bind.ok,
  });
  const rows = filterDeskRows(painted, input.market);

  return {
    season: input.season,
    week: input.week,
    count: rows.length,
    rows,
    filters: {
      market: input.market,
      minProbEdge: input.minProbEdge,
      minLineEdge: input.minLineEdge,
      minConfidence: input.minConfidence,
    },
    propsSurface: "gated",
    propsStatus: NFL_EDGES_PROPS_STATUS,
    observed,
    marketAsOf: observed.linesAsOf,
    marketBooks: (input.fairBooks ?? []).filter(Boolean),
    deskComplete: false,
    diagnostics: {
      gameCandidates: (input.fairEdges ?? []).length,
      propCandidates: 0,
      fairLinesError: input.fairLinesError,
      propsOmitted: true,
      edgeRowsBlocked: true,
      bindReason: bind.reason,
      provenanceReason: slot.reason,
    },
  };
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
  /** Fair-lines upstream abort (page-data uses pageData budget). */
  timeoutMs?: number;
  /**
   * Page-data: fair-lines timeout/transport throws so the route can 503/504
   * instead of returning a desk with fairLinesError + null marketAsOf.
   */
  throwOnTransportError?: boolean;
}): Promise<NflEdgesDeskResponse> {
  const market = params.market ?? "all";
  const minProbEdge = params.minProbEdge ?? 0.02;
  const minLineEdge = params.minLineEdge ?? 1.0;
  const minConfidence = params.minConfidence ?? 0;
  const daysAhead = params.daysAhead ?? 120;
  void params.propLimit;

  // N-1 / X-4 / E-2: first build fetches Fair Lines only. Do not fan out
  // to edges/today (edge-language unadopted) or props (absent / unavailable).
  const fairBoard = await fetchNflFairLines({
    season: params.season,
    daysAhead,
    timeoutMs: params.timeoutMs,
    throwOnTransportError: params.throwOnTransportError,
  });

  // Desk week is authoritative — do not mix forward-week fair-lines into W1.
  const weekLines = fairBoard.lines.filter(
    (line) => line.week == null || line.week === params.week,
  );
  const fairEdges = weekLines.flatMap((line) =>
    deskEdgesFromFairLine(line, { minProbEdge, minLineEdge }),
  );

  return assembleNflEdgesDeskPayload({
    season: params.season,
    week: params.week,
    market,
    minProbEdge,
    minLineEdge,
    minConfidence,
    fairOddsAsOf: fairBoard.oddsAsOf?.trim() || null,
    fairBooks: fairBoard.diagnostics.bookmakers ?? [],
    fairLinesError: fairBoard.error,
    fairEdges,
  });
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
