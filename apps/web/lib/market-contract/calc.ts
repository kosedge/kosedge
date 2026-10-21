/**
 * Canonical calculation helpers for MLB/NHL market contracts (research-only).
 *
 * Explicit side/orientation — no overloaded `*Home` semantics without a contract id.
 * Fail closed on malformed / non-finite / missing authoritative market.
 */

import {
  type HomeAwayOrientation,
  type MarketContractId,
  type SelectedSide,
  getMarketContract,
} from "./types";

export type CalcStatus = "ok" | "DATA_GAP";

export type AmericanProbResult = {
  status: CalcStatus;
  impliedProb: number | null;
  reason?: string;
};

export type NoVigResult = {
  status: CalcStatus;
  homeProb: number | null;
  awayProb: number | null;
  reason?: string;
};

export type SideEdgeResult = {
  status: CalcStatus;
  market_contract_id: MarketContractId;
  selectedSide: SelectedSide | null;
  advantage: number | null;
  signed: number | null;
  favoriteSide: SelectedSide | null;
  reason?: string;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** American → implied win probability (with vig). Fail closed if invalid. */
export function americanToImpliedProb(price: unknown): AmericanProbResult {
  if (!isFiniteNumber(price) || price === 0) {
    return { status: "DATA_GAP", impliedProb: null, reason: "non_finite_or_zero" };
  }
  if (Math.abs(price) < 100) {
    return { status: "DATA_GAP", impliedProb: null, reason: "invalid_american_abs_lt_100" };
  }
  const implied =
    price > 0 ? 100 / (price + 100) : Math.abs(price) / (Math.abs(price) + 100);
  if (!Number.isFinite(implied)) {
    return { status: "DATA_GAP", impliedProb: null, reason: "non_finite_implied" };
  }
  return { status: "ok", impliedProb: implied };
}

export function impliedProbToAmerican(prob: unknown): AmericanProbResult & {
  american: number | null;
} {
  if (!isFiniteNumber(prob) || prob <= 0 || prob >= 1) {
    return {
      status: "DATA_GAP",
      impliedProb: null,
      american: null,
      reason: "prob_out_of_open_unit_interval",
    };
  }
  const american = prob >= 0.5 ? -Math.round((100 * prob) / (1 - prob)) : Math.round((100 * (1 - prob)) / prob);
  return { status: "ok", impliedProb: prob, american };
}

/** Two-way no-vig from home/away Americans. */
export function removeVigTwoWay(
  homeAmerican: unknown,
  awayAmerican: unknown,
): NoVigResult {
  const home = americanToImpliedProb(homeAmerican);
  const away = americanToImpliedProb(awayAmerican);
  if (home.status !== "ok" || away.status !== "ok") {
    return {
      status: "DATA_GAP",
      homeProb: null,
      awayProb: null,
      reason: home.reason ?? away.reason ?? "invalid_leg",
    };
  }
  const total = (home.impliedProb as number) + (away.impliedProb as number);
  if (!(total > 0) || !Number.isFinite(total)) {
    return {
      status: "DATA_GAP",
      homeProb: null,
      awayProb: null,
      reason: "non_finite_vig_total",
    };
  }
  return {
    status: "ok",
    homeProb: (home.impliedProb as number) / total,
    awayProb: (away.impliedProb as number) / total,
  };
}

/**
 * Orient a handicap line to home-signed.
 * Odds-API NHL spreads are often away-signed; KEI puck is home-signed.
 */
export function toHomeSignedLine(
  line: unknown,
  orientation: HomeAwayOrientation,
): { status: CalcStatus; homeSigned: number | null; reason?: string } {
  if (!isFiniteNumber(line)) {
    return { status: "DATA_GAP", homeSigned: null, reason: "non_finite_line" };
  }
  if (orientation === "home_signed" || orientation === "side_explicit") {
    return { status: "ok", homeSigned: line };
  }
  if (orientation === "away_signed") {
    return { status: "ok", homeSigned: -line };
  }
  return {
    status: "DATA_GAP",
    homeSigned: null,
    reason: "orientation_not_applicable",
  };
}

/** Favorite/underdog from home-signed handicap (negative ⇒ home favorite). */
export function favoriteFromHomeSignedHandicap(homeSigned: number): {
  favorite: SelectedSide;
  underdog: SelectedSide;
} {
  if (homeSigned < 0) return { favorite: "home", underdog: "away" };
  if (homeSigned > 0) return { favorite: "away", underdog: "home" };
  // pick'em — treat as no favorite; caller may fail closed
  return { favorite: "home", underdog: "away" };
}

/**
 * Moneyline selected-side edge (probability points).
 * signed = modelHomeProb − marketNoVigHomeProb
 * Home when signed ≥ 0; Away when < 0. Display = positive magnitude.
 */
export function moneylineSelectedSideEdge(args: {
  market_contract_id: MarketContractId;
  modelHomeProb: unknown;
  marketNoVigHomeProb: unknown;
}): SideEdgeResult {
  const contract = getMarketContract(args.market_contract_id);
  if (!contract || contract.family !== "moneyline") {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "missing_or_non_ml_contract",
    };
  }
  if (contract.period_scope === "regulation") {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "regulation_three_way_requires_explicit_draw_path",
    };
  }
  if (
    !isFiniteNumber(args.modelHomeProb) ||
    !isFiniteNumber(args.marketNoVigHomeProb)
  ) {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "missing_authoritative_prob",
    };
  }
  const signed = args.modelHomeProb - args.marketNoVigHomeProb;
  return {
    status: "ok",
    market_contract_id: args.market_contract_id,
    selectedSide: signed >= 0 ? "home" : "away",
    advantage: Math.abs(signed),
    signed,
    favoriteSide: args.modelHomeProb >= 0.5 ? "home" : "away",
  };
}

/**
 * Handicap (run line / puck line) selected-side edge in line points.
 * Home lean when (fair − market) < 0; Away when > 0.
 */
export function handicapSelectedSideEdge(args: {
  market_contract_id: MarketContractId;
  fairHomeSigned: unknown;
  marketHomeSigned: unknown;
}): SideEdgeResult {
  const contract = getMarketContract(args.market_contract_id);
  if (
    !contract ||
    (contract.family !== "run_line" && contract.family !== "puck_line")
  ) {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "missing_or_non_handicap_contract",
    };
  }
  if (
    !isFiniteNumber(args.fairHomeSigned) ||
    !isFiniteNumber(args.marketHomeSigned)
  ) {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "missing_authoritative_market",
    };
  }
  const signed = args.fairHomeSigned - args.marketHomeSigned;
  const fav = favoriteFromHomeSignedHandicap(args.marketHomeSigned);
  return {
    status: "ok",
    market_contract_id: args.market_contract_id,
    selectedSide: signed < 0 ? "home" : "away",
    advantage: Math.abs(signed),
    signed,
    favoriteSide: fav.favorite,
  };
}

/** Totals selected-side edge. Over when (fair − market) > 0. */
export function totalSelectedSideEdge(args: {
  market_contract_id: MarketContractId;
  fairTotal: unknown;
  marketTotal: unknown;
}): SideEdgeResult {
  const contract = getMarketContract(args.market_contract_id);
  if (!contract || contract.family !== "total") {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "missing_or_non_total_contract",
    };
  }
  if (!isFiniteNumber(args.fairTotal) || !isFiniteNumber(args.marketTotal)) {
    return {
      status: "DATA_GAP",
      market_contract_id: args.market_contract_id,
      selectedSide: null,
      advantage: null,
      signed: null,
      favoriteSide: null,
      reason: "missing_authoritative_market",
    };
  }
  const signed = args.fairTotal - args.marketTotal;
  return {
    status: "ok",
    market_contract_id: args.market_contract_id,
    selectedSide: signed > 0 ? "over" : "under",
    advantage: Math.abs(signed),
    signed,
    favoriteSide: null,
  };
}

/**
 * Fail closed when displayed Book line disagrees with the edge SoT line
 * beyond tolerance (customer-truth disagreement).
 */
export function reconcileDisplayedBookVsEdgeSot(args: {
  displayedBook: unknown;
  edgeSotMarket: unknown;
  tolerance?: number;
}): { status: CalcStatus; reason?: string } {
  const tol = args.tolerance ?? 0.051;
  if (!isFiniteNumber(args.displayedBook) || !isFiniteNumber(args.edgeSotMarket)) {
    return { status: "DATA_GAP", reason: "missing_book_or_sot" };
  }
  if (Math.abs(args.displayedBook - args.edgeSotMarket) <= tol) {
    return { status: "ok" };
  }
  if (
    Math.round(args.displayedBook * 10) === Math.round(args.edgeSotMarket * 10)
  ) {
    return { status: "ok" };
  }
  return { status: "DATA_GAP", reason: "displayed_book_disagrees_edge_sot" };
}

/** Push/void semantics probe for known contracts. */
export function pushVoidForContract(id: MarketContractId): string | null {
  return getMarketContract(id)?.push_void ?? null;
}

/** Period/settlement separation guard. */
export function assertPeriodSettlementSeparation(
  a: MarketContractId,
  b: MarketContractId,
): { ok: boolean; reason?: string } {
  const ca = getMarketContract(a);
  const cb = getMarketContract(b);
  if (!ca || !cb) return { ok: false, reason: "missing_contract" };
  if (
    ca.sport === cb.sport &&
    ca.family === cb.family &&
    (ca.period_scope !== cb.period_scope ||
      ca.settlement_scope !== cb.settlement_scope)
  ) {
    return { ok: true, reason: "distinct_period_or_settlement" };
  }
  if (a === b) return { ok: false, reason: "same_contract" };
  return { ok: true };
}
