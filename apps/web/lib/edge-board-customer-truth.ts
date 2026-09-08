/**
 * Shared Edge Board / Edges-desk customer-truth contract.
 *
 * Handicap (spread / puck-line / run-line / similar):
 *   selectedSideAdvantage = abs(fairLine − displayedMarketLine)
 *   Home lean when (fair − market) < 0; Away when > 0
 *   Display = positive magnitude only (never green-negative selected-side edge)
 *   Displayed market MUST be the exact line used to calculate the edge
 *
 * Totals (own formula — do not reuse handicap wording blindly):
 *   selectedSideAdvantage = abs(fairTotal − displayedMarketTotal)
 *   Over when (fair − market) > 0; Under when < 0
 *   Display = positive magnitude
 *
 * Moneyline (own formula — probability points, not line points):
 *   selectedSideAdvantage = abs(modelHomeProb − marketNoVigHomeProb)
 *   Home when signed ≥ 0; Away when < 0
 *   Display = positive pp magnitude
 *
 * Fail closed: any Fair / Market / Edge disagreement → no painted edge.
 */

export type EdgeBoardSportKey =
  | "nfl"
  | "cfb"
  | "nba"
  | "nhl"
  | "mlb"
  | "wnba"
  | "ncaam";

/** Sports with a public `/edge-board/{sport}` surface. */
export const EDGE_BOARD_SPORTS: readonly EdgeBoardSportKey[] = [
  "nfl",
  "cfb",
  "nba",
  "nhl",
  "mlb",
  "wnba",
  "ncaam",
] as const;

export type HandicapSide = "Home" | "Away";
export type TotalSide = "Over" | "Under";
export type MlSide = "Home" | "Away";

export type CustomerTruthStatus = "ok" | "DATA_GAP";

/** Half-point display quantum — calc vs display must agree at 0.1 after round. */
export const EDGE_ARITH_TOLERANCE = 0.051;

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function edgeMagnitudesAgree(
  calculated: number,
  claimed: number,
  tolerance: number = EDGE_ARITH_TOLERANCE,
): boolean {
  if (!isFiniteNumber(calculated) || !isFiniteNumber(claimed)) return false;
  if (Math.abs(calculated - claimed) <= tolerance) return true;
  // Display often rounds to 1 decimal — require same tenth.
  return (
    Math.round(calculated * 10) === Math.round(claimed * 10) ||
    Math.round(calculated * 10) === Math.round(Math.abs(claimed) * 10)
  );
}

/** Handicap / spread / puck-line / run-line selected-side contract. */
export function handicapSelectedSideAdvantage(args: {
  fairLine: number;
  marketLine: number;
}): {
  signed: number;
  advantage: number;
  side: HandicapSide;
} {
  const signed = args.fairLine - args.marketLine;
  return {
    signed,
    advantage: Math.abs(signed),
    side: signed < 0 ? "Home" : "Away",
  };
}

/** Totals selected-side contract (points / runs / goals). */
export function totalSelectedSideAdvantage(args: {
  fairTotal: number;
  marketTotal: number;
}): {
  signed: number;
  advantage: number;
  side: TotalSide;
} {
  const signed = args.fairTotal - args.marketTotal;
  return {
    signed,
    advantage: Math.abs(signed),
    side: signed > 0 ? "Over" : "Under",
  };
}

/** Moneyline selected-side contract (probability edge, not American-odds delta). */
export function moneylineSelectedSideAdvantage(args: {
  /** model_home_prob − market_no_vig_home (or equivalent signed home ML edge). */
  signedProbEdge: number;
}): {
  signed: number;
  advantage: number;
  side: MlSide;
} {
  const signed = args.signedProbEdge;
  return {
    signed,
    advantage: Math.abs(signed),
    side: signed >= 0 ? "Home" : "Away",
  };
}

export type ReconciledHandicapEdge = {
  status: CustomerTruthStatus;
  fairLine: number;
  marketLine: number;
  /** Positive selected-side magnitude only when status=ok. */
  advantage: number | null;
  side: HandicapSide | null;
  /** Signed home-perspective delta (internal / diagnostics). */
  signed: number | null;
  reason?: string;
};

/**
 * Reconcile handicap Fair + Market + claimed edge.
 * Claimed edge may be signed (legacy desk) or magnitude — compared via abs.
 * On disagreement → DATA_GAP (fail closed, no painted edge).
 */
export function reconcileHandicapCustomerEdge(args: {
  fairLine: number | null | undefined;
  marketLine: number | null | undefined;
  /** Server/home-signed edge or magnitude — abs compared to |fair−market|. */
  claimedEdge?: number | null;
}): ReconciledHandicapEdge {
  const fair = args.fairLine;
  const market = args.marketLine;
  if (!isFiniteNumber(fair) || !isFiniteNumber(market)) {
    return {
      status: "DATA_GAP",
      fairLine: isFiniteNumber(fair) ? fair : NaN,
      marketLine: isFiniteNumber(market) ? market : NaN,
      advantage: null,
      side: null,
      signed: null,
      reason: "missing_fair_or_market",
    };
  }
  const { signed, advantage, side } = handicapSelectedSideAdvantage({
    fairLine: fair,
    marketLine: market,
  });
  if (args.claimedEdge != null && isFiniteNumber(args.claimedEdge)) {
    if (!edgeMagnitudesAgree(advantage, Math.abs(args.claimedEdge))) {
      return {
        status: "DATA_GAP",
        fairLine: fair,
        marketLine: market,
        advantage: null,
        side: null,
        signed: null,
        reason: "fair_market_edge_mismatch",
      };
    }
  }
  return {
    status: "ok",
    fairLine: fair,
    marketLine: market,
    advantage,
    side,
    signed,
  };
}

export type ReconciledTotalEdge = {
  status: CustomerTruthStatus;
  fairTotal: number;
  marketTotal: number;
  advantage: number | null;
  side: TotalSide | null;
  signed: number | null;
  reason?: string;
};

export function reconcileTotalCustomerEdge(args: {
  fairTotal: number | null | undefined;
  marketTotal: number | null | undefined;
  claimedEdge?: number | null;
}): ReconciledTotalEdge {
  const fair = args.fairTotal;
  const market = args.marketTotal;
  if (!isFiniteNumber(fair) || !isFiniteNumber(market)) {
    return {
      status: "DATA_GAP",
      fairTotal: isFiniteNumber(fair) ? fair : NaN,
      marketTotal: isFiniteNumber(market) ? market : NaN,
      advantage: null,
      side: null,
      signed: null,
      reason: "missing_fair_or_market",
    };
  }
  const { signed, advantage, side } = totalSelectedSideAdvantage({
    fairTotal: fair,
    marketTotal: market,
  });
  if (args.claimedEdge != null && isFiniteNumber(args.claimedEdge)) {
    if (!edgeMagnitudesAgree(advantage, Math.abs(args.claimedEdge))) {
      return {
        status: "DATA_GAP",
        fairTotal: fair,
        marketTotal: market,
        advantage: null,
        side: null,
        signed: null,
        reason: "fair_market_edge_mismatch",
      };
    }
  }
  return {
    status: "ok",
    fairTotal: fair,
    marketTotal: market,
    advantage,
    side,
    signed,
  };
}

export type ReconciledMlEdge = {
  status: CustomerTruthStatus;
  advantage: number | null;
  side: MlSide | null;
  signed: number | null;
  reason?: string;
};

export function reconcileMoneylineCustomerEdge(args: {
  signedProbEdge: number | null | undefined;
}): ReconciledMlEdge {
  const signed = args.signedProbEdge;
  if (!isFiniteNumber(signed)) {
    return {
      status: "DATA_GAP",
      advantage: null,
      side: null,
      signed: null,
      reason: "missing_ml_edge",
    };
  }
  const out = moneylineSelectedSideAdvantage({ signedProbEdge: signed });
  return {
    status: "ok",
    advantage: out.advantage,
    side: out.side,
    signed: out.signed,
  };
}

/** Format selected-side handicap/total advantage for customer chrome. */
export function formatSelectedSideLineEdge(
  advantage: number,
  unit: "pts" | "runs" | "goals" = "pts",
): string {
  const mag = Math.abs(advantage);
  return `+${mag.toFixed(1)} ${unit}`;
}

/** Format selected-side ML advantage (probability points). Always non-negative. */
export function formatSelectedSideProbEdge(advantage: number): string {
  const pp = Math.abs(advantage) * 100;
  return `+${pp.toFixed(1)}pp`;
}

/**
 * Prefer stakeable close for edge calc/display identity.
 * Priority matches `resolveMarketLineForEdge` / model stake_close.
 */
export function pickEdgeMarketLine(args: {
  stake?: number | null;
  dk?: number | null;
  fd?: number | null;
  market?: number | null;
  best?: number | null;
  /** Optional sanitizer (spread/total hygiene). Pass-through when omitted. */
  sanitize?: (n: number) => number | null;
}): number | null {
  const sanitize =
    args.sanitize ?? ((n: number) => (isFiniteNumber(n) ? n : null));
  for (const v of [args.stake, args.dk, args.fd, args.market, args.best]) {
    if (!isFiniteNumber(v)) continue;
    const cleaned = sanitize(v);
    if (cleaned != null) return cleaned;
  }
  return null;
}

/**
 * Fail-closed scrub for Action Fair/Mkt/Edge triples on Edge Board rows.
 * Returns positive magnitude or null (hide edge chrome).
 */
export function scrubActionEdgeMagnitude(args: {
  fair: number | null | undefined;
  market: number | null | undefined;
  edgeMagnitude: number | null | undefined;
  kind: "handicap" | "total";
}): number | undefined {
  if (!isFiniteNumber(args.fair) || !isFiniteNumber(args.market)) {
    return undefined;
  }
  const reconciled =
    args.kind === "total"
      ? reconcileTotalCustomerEdge({
          fairTotal: args.fair,
          marketTotal: args.market,
          claimedEdge: args.edgeMagnitude,
        })
      : reconcileHandicapCustomerEdge({
          fairLine: args.fair,
          marketLine: args.market,
          claimedEdge: args.edgeMagnitude,
        });
  if (reconciled.status !== "ok" || reconciled.advantage == null) {
    return undefined;
  }
  // Always return positive magnitude.
  return Math.abs(reconciled.advantage);
}

export type CustomerTruthAuditFinding = {
  id: string;
  sport: string;
  surface: "edge-board" | "edges-desk";
  marketType: string;
  issue: "sign" | "arithmetic" | "missing_pair";
  detail: string;
};

export type CustomerTruthAuditSummary = {
  sport: string;
  surface: "edge-board" | "edges-desk";
  rowsScanned: number;
  handicapRows: number;
  signInconsistencies: number;
  arithmeticInconsistencies: number;
  findings: CustomerTruthAuditFinding[];
};

/**
 * Audit desk-shaped rows (kosedgeLine / marketLine / edge / side).
 * Used by regression tests across full slates.
 */
export function auditDeskHandicapRows(args: {
  sport: string;
  rows: Array<{
    id?: string;
    marketType?: string;
    matchupOrPlayer?: string;
    matchup?: string;
    kosedgeLine?: string | null;
    marketLine?: string | null;
    edge?: number | null;
    edgeDisplay?: string | null;
    side?: string | null;
  }>;
}): CustomerTruthAuditSummary {
  const findings: CustomerTruthAuditFinding[] = [];
  let handicapRows = 0;
  let signInconsistencies = 0;
  let arithmeticInconsistencies = 0;

  for (const row of args.rows) {
    const mt = String(row.marketType ?? "");
    if (mt !== "spread" && mt !== "run_line" && mt !== "puck_line") continue;
    handicapRows += 1;
    const fair = parseSignedLine(row.kosedgeLine);
    const market = parseSignedLine(row.marketLine);
    const edge = row.edge;
    const id = row.id ?? String(row.matchupOrPlayer ?? row.matchup ?? "row");

    if (edge != null && isFiniteNumber(edge) && edge < 0) {
      signInconsistencies += 1;
      findings.push({
        id,
        sport: args.sport,
        surface: "edges-desk",
        marketType: mt,
        issue: "sign",
        detail: `selected-side edgeDisplay must be positive magnitude; got ${row.edgeDisplay ?? edge}`,
      });
    }

    if (
      fair != null &&
      market != null &&
      edge != null &&
      isFiniteNumber(edge)
    ) {
      const calc = Math.abs(fair - market);
      if (!edgeMagnitudesAgree(calc, Math.abs(edge))) {
        arithmeticInconsistencies += 1;
        findings.push({
          id,
          sport: args.sport,
          surface: "edges-desk",
          marketType: mt,
          issue: "arithmetic",
          detail: `abs(fair−market)=${calc.toFixed(3)} vs |edge|=${Math.abs(edge).toFixed(3)} (fair=${fair}, mkt=${market})`,
        });
      }
    }
  }

  return {
    sport: args.sport,
    surface: "edges-desk",
    rowsScanned: args.rows.length,
    handicapRows,
    signInconsistencies,
    arithmeticInconsistencies,
    findings,
  };
}

/**
 * Audit Edge Board Action triples (fairLine / decisionMarketLine / edgeMagnitude).
 */
export function auditEdgeBoardActionRows(args: {
  sport: string;
  rows: Array<{
    id?: string;
    game?: string;
    market?: string;
    fairLine?: number | null;
    decisionMarketLine?: number | null;
    edgeMagnitude?: number | null;
  }>;
}): CustomerTruthAuditSummary {
  const findings: CustomerTruthAuditFinding[] = [];
  let handicapRows = 0;
  let signInconsistencies = 0;
  let arithmeticInconsistencies = 0;

  for (const row of args.rows) {
    const market = String(row.market ?? "");
    const isHandicap =
      market === "Spread" ||
      market === "Puck Line" ||
      market === "Run Line" ||
      /line/i.test(market);
    const isTotal = market === "Total" || /total/i.test(market);
    if (!isHandicap && !isTotal) continue;
    if (isHandicap) handicapRows += 1;

    const id = row.id ?? String(row.game ?? "row");
    const fair = row.fairLine;
    const mkt = row.decisionMarketLine;
    const edge = row.edgeMagnitude;

    if (edge != null && isFiniteNumber(edge) && edge < 0) {
      signInconsistencies += 1;
      findings.push({
        id,
        sport: args.sport,
        surface: "edge-board",
        marketType: market,
        issue: "sign",
        detail: `edgeMagnitude must be >= 0; got ${edge}`,
      });
    }

    if (
      fair != null &&
      mkt != null &&
      isFiniteNumber(fair) &&
      isFiniteNumber(mkt)
    ) {
      if (edge == null || !isFiniteNumber(edge)) {
        // Fail-closed empty edge with both lines present is allowed (PASS / below threshold),
        // but if chrome paints an edge it must reconcile — missing edge is not an arith bug.
        continue;
      }
      const calc = Math.abs(fair - mkt);
      if (!edgeMagnitudesAgree(calc, Math.abs(edge))) {
        arithmeticInconsistencies += 1;
        findings.push({
          id,
          sport: args.sport,
          surface: "edge-board",
          marketType: market,
          issue: "arithmetic",
          detail: `abs(fair−mkt)=${calc.toFixed(3)} vs edgeMagnitude=${edge} (fair=${fair}, mkt=${mkt})`,
        });
      }
    }
  }

  return {
    sport: args.sport,
    surface: "edge-board",
    rowsScanned: args.rows.length,
    handicapRows,
    signInconsistencies,
    arithmeticInconsistencies,
    findings,
  };
}

function parseSignedLine(raw: string | null | undefined): number | null {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (!s || s === "—" || s.toUpperCase() === "DATA GAP") return null;
  const n = Number(s.replace(/[^+\-\d.]/g, ""));
  return Number.isFinite(n) ? n : null;
}
