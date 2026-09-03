/**
 * KosEdge NFL Decision Engine (Edge Board Tag Policy + Play-To).
 *
 * Doctrine: we bet prices, not teams.
 *
 * Contract
 * --------
 * - Model research fair → research only (no PLAY from Model alone).
 * - KEI reprice → published handicap; Fair for tags.
 * - Edge / Tag → KEI vs best available market only (this module).
 * - Thresholds: `nfl-tag-policy.ts` (do not duplicate).
 *
 * Mirrors services/model-service/src/services/nfl_decision_engine.py
 */

export {
  BREAKEVEN_ATS_MINUS_110,
  CONFIDENCE_BEST_BET_MIN,
  CONFIDENCE_PLAY_MIN,
  CONFIDENCE_TIER_BASE,
  COVER_LEAN_MAX,
  COVER_MODEL_WARNING,
  COVER_PASS_MAX,
  COVER_PLAY_MAX,
  COVER_STRONG_MAX,
  EARLY_SIDE,
  INSEASON_SIDE,
  SPREAD_KEY_NUMBERS,
  STANDARD_SIDE,
  TOTAL_KEY_NUMBERS,
  TOTAL_PASS_MAX,
  TOTAL_STRONG_MIN,
  sideThresholdsForWeek,
  totalThresholdsForWeek,
  weekRegime,
  type SidePointThresholds,
  type WeekRegime,
} from "./nfl-tag-policy";

import {
  CONFIDENCE_BEST_BET_MIN,
  CONFIDENCE_PLAY_MIN,
  CONFIDENCE_TIER_BASE,
  COVER_LEAN_MAX,
  COVER_MODEL_WARNING,
  COVER_PASS_MAX,
  COVER_PLAY_MAX,
  COVER_STRONG_MAX,
  SPREAD_KEY_NUMBERS,
  TOTAL_KEY_NUMBERS,
  sideThresholdsForWeek,
  totalThresholdsForWeek,
  weekRegime,
  type WeekRegime,
} from "./nfl-tag-policy";
import {
  SPREAD_PLAY_MAX,
  SPREAD_PLAY_MIN,
  TOTAL_PLAY_ENABLED,
  spreadEdgeInPlayBand,
} from "./nfl-spread-play-lock";

export type ActionLabel =
  | "PASS"
  | "LEAN"
  | "PLAY"
  | "BEST VALUE"
  | "ALERT"
  | "STAY AWAY";

export type PointGrade =
  | "PASS"
  | "LEAN"
  | "PLAY"
  | "STRONG PLAY"
  | "EXCEPTIONAL";

export type DecisionMarket = "spread" | "total";
export type ConfidenceBand = "LOW" | "MEDIUM" | "HIGH";

export type PlayToLadder = {
  sideOrTotal: string;
  playTo: number;
  leanTo: number;
  passFrom: number;
  fairLine: number;
  marketLine: number;
  edgePoints: number;
  notes: string;
};

export type MarketConfirmation = {
  modelFair: number | null;
  opening: number | null;
  current: number | null;
  closing: number | null;
  confirmsThesis: boolean | null;
  weakensThesis: boolean | null;
  note: string;
};

export type ConfidenceAssessment = {
  score: number;
  band: ConfidenceBand;
  factors: Record<string, unknown>;
  unresolvedFlags: string[];
};

export type DecisionResult = {
  market: DecisionMarket;
  actionLabel: ActionLabel;
  pointGrade: PointGrade;
  edgeMagnitude: number;
  modelConfidence: ConfidenceAssessment;
  coverProb: number | null;
  coverGrade: PointGrade | null;
  playTo: PlayToLadder | null;
  marketConfirmation: MarketConfirmation;
  isBestBet: boolean;
  modelWarning: boolean;
  keyNumberCross: boolean;
  priceStillAvailable: boolean;
  numericalEdge: boolean;
  confidenceOk: boolean;
  reason: string;
  week: number | null;
  weekRegime: WeekRegime;
  fairLine: number | null;
  marketLine: number | null;
};

export function confidenceBand(score: number): ConfidenceBand {
  const s = Math.max(0, Math.min(1, score));
  if (s >= 0.75) return "HIGH";
  if (s >= 0.55) return "MEDIUM";
  return "LOW";
}

export function isTierConstantConfidence(
  assessment: Pick<ConfidenceAssessment, "score" | "unresolvedFlags"> & {
    factors?: ConfidenceAssessment["factors"];
  },
): boolean {
  if (assessment.unresolvedFlags.length > 0) return false;
  const hf = assessment.factors?.historicalFit;
  if (typeof hf === "number" && Number.isFinite(hf)) {
    return false;
  }
  return Math.abs(assessment.score - CONFIDENCE_TIER_BASE) < 1e-9;
}

export function assessConfidence(
  args: {
    baseScore?: number | null;
    schemeStable?: boolean;
    injuryClear?: boolean;
    weatherClear?: boolean;
    qbClear?: boolean;
    historicalFit?: number | null;
    conflictingInputs?: boolean;
    liquidityOk?: boolean;
    extraFlags?: string[];
  } = {},
): ConfidenceAssessment {
  let score = args.baseScore == null ? CONFIDENCE_TIER_BASE : Number(args.baseScore);
  const flags: string[] = [];
  if (args.schemeStable === false) {
    score -= 0.12;
    flags.push("scheme_unstable");
  }
  if (args.injuryClear === false) {
    score -= 0.18;
    flags.push("injury_unresolved");
  }
  if (args.weatherClear === false) {
    score -= 0.1;
    flags.push("weather_unresolved");
  }
  if (args.qbClear === false) {
    score -= 0.22;
    flags.push("qb_unresolved");
  }
  if (args.conflictingInputs) {
    score -= 0.25;
    flags.push("conflicting_inputs");
  }
  if (args.liquidityOk === false) {
    score -= 0.08;
    flags.push("liquidity_thin");
  }
  if (args.historicalFit != null && Number.isFinite(args.historicalFit)) {
    const hf = Math.max(0, Math.min(1, Number(args.historicalFit)));
    score = 0.7 * score + 0.3 * hf;
  }
  if (args.extraFlags?.length) flags.push(...args.extraFlags.filter(Boolean));
  score = Math.max(0, Math.min(1, Math.round(score * 10000) / 10000));
  return {
    score,
    band: confidenceBand(score),
    factors: {
      schemeStable: args.schemeStable !== false,
      injuryClear: args.injuryClear !== false,
      weatherClear: args.weatherClear !== false,
      qbClear: args.qbClear !== false,
      conflictingInputs: Boolean(args.conflictingInputs),
      liquidityOk: args.liquidityOk !== false,
      historicalFit: args.historicalFit ?? null,
    },
    unresolvedFlags: flags,
  };
}

export function gradeSidePoints(
  absEdge: number,
  week?: number | null,
): PointGrade {
  const e = Math.abs(Number(absEdge));
  const t = sideThresholdsForWeek(week);
  if (e < t.passMax) return "PASS";
  if (e < t.playMin) return "LEAN";
  if (e < t.strongMin) return "PLAY";
  return "STRONG PLAY";
}

export function gradeTotalPoints(
  absEdge: number,
  week?: number | null,
): PointGrade {
  const e = Math.abs(Number(absEdge));
  const t = totalThresholdsForWeek(week);
  if (e < t.passMax) return "PASS";
  if (e < t.playMin) return "LEAN";
  if (e < t.strongMin) return "PLAY";
  return "STRONG PLAY";
}

export function gradeCoverProb(
  coverProb: number | null | undefined,
): PointGrade | null {
  if (coverProb == null || !Number.isFinite(coverProb)) return null;
  const p = Number(coverProb);
  if (p < COVER_PASS_MAX) return "PASS";
  if (p < COVER_LEAN_MAX) return "LEAN";
  if (p < COVER_PLAY_MAX) return "PLAY";
  if (p < COVER_STRONG_MAX) return "STRONG PLAY";
  return "EXCEPTIONAL";
}

export function crossesKeyNumber(
  fair: number,
  market: number,
  marketKind: DecisionMarket = "spread",
): boolean {
  const keys = marketKind === "spread" ? SPREAD_KEY_NUMBERS : TOTAL_KEY_NUMBERS;
  const lo = Math.min(fair, market);
  const hi = Math.max(fair, market);
  if (hi <= lo) return false;
  for (const k of keys) {
    if ((lo < k && k < hi) || (lo < -k && -k < hi)) return true;
  }
  return false;
}

export function preferKeyNumberEdge(
  absEdgeA: number,
  crossesA: boolean,
  absEdgeB: number,
  crossesB: boolean,
): "a" | "b" | "tie" {
  if (Math.abs(absEdgeA - absEdgeB) < 1e-9) {
    if (crossesA && !crossesB) return "a";
    if (crossesB && !crossesA) return "b";
    return "tie";
  }
  if (crossesA && !crossesB && absEdgeA + 0.5 >= absEdgeB) return "a";
  if (crossesB && !crossesA && absEdgeB + 0.5 >= absEdgeA) return "b";
  return absEdgeA > absEdgeB ? "a" : "b";
}

function roundHalf(x: number): number {
  return Math.round(x * 2) / 2;
}

function fmtSigned(n: number): string {
  if (Object.is(n, -0) || n === 0) return "+0";
  return n > 0 ? `+${n}` : String(n);
}

/**
 * Play-to from KEI + week thresholds.
 * Remaining |KEI − price| at play_to = playMin; lean_to = leanMax; pass_from = passMax.
 */
export function buildSidePlayToLadder(args: {
  fairSpreadHome: number;
  marketSpreadHome: number;
  homeAbbr?: string;
  awayAbbr?: string;
  week?: number | null;
}): PlayToLadder {
  const fair = args.fairSpreadHome;
  const market = args.marketSpreadHome;
  const edge = fair - market;
  const absEdge = Math.abs(edge);
  const t = sideThresholdsForWeek(args.week);
  const likesHome = edge < 0;

  if (likesHome) {
    const team = args.homeAbbr ?? "HOME";
    let playTo = roundHalf(fair + t.playMin);
    let leanTo = roundHalf(fair + t.leanMax);
    let passFrom = roundHalf(fair + t.passMax);
    const ordered = [playTo, leanTo, passFrom].sort((a, b) => b - a);
    playTo = ordered[0]!;
    leanTo = ordered[1]!;
    passFrom = ordered[2]!;
    return {
      sideOrTotal: `${team} ${fmtSigned(market)}`,
      playTo,
      leanTo,
      passFrom,
      fairLine: fair,
      marketLine: market,
      edgePoints: Math.round(absEdge * 1000) / 1000,
      notes: `Play ${team} to ${fmtSigned(playTo)}; lean ${fmtSigned(leanTo)}; pass ${fmtSigned(passFrom)} or worse`,
    };
  }

  const team = args.awayAbbr ?? "AWAY";
  const marketNum = -market;
  let playTo = roundHalf(-(fair - t.playMin));
  let leanTo = roundHalf(-(fair - t.leanMax));
  let passFrom = roundHalf(-(fair - t.passMax));
  const ordered = [playTo, leanTo, passFrom].sort((a, b) => b - a);
  playTo = ordered[0]!;
  leanTo = ordered[1]!;
  passFrom = ordered[2]!;
  return {
    sideOrTotal: `${team} ${fmtSigned(marketNum)}`,
    playTo,
    leanTo,
    passFrom,
    fairLine: fair,
    marketLine: market,
    edgePoints: Math.round(absEdge * 1000) / 1000,
    notes: `Play ${team} to ${fmtSigned(playTo)}; lean ${fmtSigned(leanTo)}; pass ${fmtSigned(passFrom)} or worse`,
  };
}

export function buildTotalPlayToLadder(args: {
  fairTotal: number;
  marketTotal: number;
  week?: number | null;
}): PlayToLadder {
  const fair = args.fairTotal;
  const market = args.marketTotal;
  const edge = fair - market;
  const absEdge = Math.abs(edge);
  const t = totalThresholdsForWeek(args.week);
  const likesOver = edge > 0;
  const m = market;

  if (likesOver) {
    let playTo = roundHalf(fair - t.playMin);
    let leanTo = roundHalf(fair - t.leanMax);
    let passFrom = roundHalf(fair - t.passMax);
    const ordered = [playTo, leanTo, passFrom].sort((a, b) => a - b);
    playTo = ordered[0]!;
    leanTo = ordered[1]!;
    passFrom = ordered[2]!;
    return {
      sideOrTotal: `Over ${m}`,
      playTo,
      leanTo,
      passFrom,
      fairLine: fair,
      marketLine: market,
      edgePoints: Math.round(absEdge * 1000) / 1000,
      notes: `Play Over ${playTo} or better; lean to ${leanTo}; pass ${passFrom}+`,
    };
  }

  let playTo = roundHalf(fair + t.playMin);
  let leanTo = roundHalf(fair + t.leanMax);
  let passFrom = roundHalf(fair + t.passMax);
  const ordered = [playTo, leanTo, passFrom].sort((a, b) => b - a);
  playTo = ordered[0]!;
  leanTo = ordered[1]!;
  passFrom = ordered[2]!;
  return {
    sideOrTotal: `Under ${m}`,
    playTo,
    leanTo,
    passFrom,
    fairLine: fair,
    marketLine: market,
    edgePoints: Math.round(absEdge * 1000) / 1000,
    notes: `Play Under ${playTo} or better; lean to ${leanTo}; pass ${passFrom} or lower`,
  };
}

export function marketPastPlayTo(args: {
  marketKind: DecisionMarket;
  fair: number;
  market: number;
  ladder: PlayToLadder;
}): boolean {
  const edge = args.fair - args.market;
  if (args.marketKind === "spread") {
    const likesHome = edge < 0;
    if (likesHome) return args.market < args.ladder.playTo - 1e-9;
    return -args.market < args.ladder.playTo - 1e-9;
  }
  const likesOver = edge > 0;
  if (likesOver) return args.market > args.ladder.playTo + 1e-9;
  return args.market < args.ladder.playTo - 1e-9;
}

export function assessMarketConfirmation(args: {
  modelFair: number | null | undefined;
  opening: number | null | undefined;
  current: number | null | undefined;
  closing?: number | null;
  likesHomeOrOver?: boolean | null;
}): MarketConfirmation {
  let confirms: boolean | null = null;
  let weakens: boolean | null = null;
  let note = "Market movement is information only; fair line unchanged.";
  if (
    args.modelFair != null &&
    args.opening != null &&
    args.current != null &&
    args.likesHomeOrOver != null
  ) {
    const move = Number(args.current) - Number(args.opening);
    const towardModel =
      (Number(args.modelFair) - Number(args.opening)) * move > 0;
    confirms = towardModel;
    weakens = !towardModel && Math.abs(move) >= 0.5;
    note = confirms
      ? "Market moved toward model fair — confirms thesis; fair unchanged."
      : weakens
        ? "Market moved away from model fair — weakens thesis; fair unchanged."
        : note;
  }
  return {
    modelFair: args.modelFair ?? null,
    opening: args.opening ?? null,
    current: args.current ?? null,
    closing: args.closing ?? null,
    confirmsThesis: confirms,
    weakensThesis: weakens,
    note,
  };
}

function pointRank(grade: PointGrade): number {
  const order: Record<PointGrade, number> = {
    PASS: 0,
    LEAN: 1,
    PLAY: 2,
    "STRONG PLAY": 3,
    EXCEPTIONAL: 4,
  };
  return order[grade];
}

/** Cover prob wins for the tag when available; both still shown. */
function coverWins(
  pointGrade: PointGrade,
  coverGrade: PointGrade | null,
): PointGrade {
  if (!coverGrade) return pointGrade;
  return coverGrade;
}

export function evaluateBestBet(args: {
  pointGrade: PointGrade;
  confidence: ConfidenceAssessment;
  priceAvailable: boolean;
  keyNumberCross: boolean;
  marketConfirmation: MarketConfirmation;
  matchupSupport: boolean;
  liquidityOk: boolean;
}): boolean {
  const largeEdge =
    args.pointGrade === "STRONG PLAY" ||
    args.pointGrade === "EXCEPTIONAL" ||
    (args.pointGrade === "PLAY" && args.keyNumberCross);
  const highConf =
    args.confidence.score >= CONFIDENCE_BEST_BET_MIN &&
    args.confidence.band === "HIGH";
  const limitedUnresolved = args.confidence.unresolvedFlags.length === 0;
  const favorableNumber =
    args.priceAvailable && !args.marketConfirmation.weakensThesis;
  return Boolean(
    largeEdge &&
      highConf &&
      favorableNumber &&
      limitedUnresolved &&
      args.matchupSupport &&
      args.liquidityOk,
  );
}

function confidenceOkForPlay(conf: ConfidenceAssessment): boolean {
  if (conf.band === "LOW") return false;
  if (conf.score < CONFIDENCE_PLAY_MIN) return false;
  if (conf.unresolvedFlags.includes("qb_unresolved")) return false;
  return true;
}

function majorUncertainty(conf: ConfidenceAssessment): boolean {
  return conf.unresolvedFlags.some((f) =>
    [
      "qb_unresolved",
      "injury_unresolved",
      "weather_unresolved",
      "conflicting_inputs",
    ].includes(f),
  );
}

/**
 * Locked spread PLAY holdout (`spread_play_v2_cap7`): never emit PLAY / BEST VALUE
 * outside 2.5 ≤ |edge| < 7.0 — covers early playMin, key-cross, and cover-prob paths.
 * See `NFL_SPREAD_PLAY_LOCKED.md`.
 */
function applySpreadPlayHoldoutBand(
  label: ActionLabel,
  absEdge: number,
  reason: string,
): { label: ActionLabel; reason: string; isBestBet: boolean } {
  if (label !== "PLAY" && label !== "BEST VALUE") {
    return { label, reason, isBestBet: label === "BEST VALUE" };
  }
  if (spreadEdgeInPlayBand(absEdge)) {
    return { label, reason, isBestBet: label === "BEST VALUE" };
  }
  if (absEdge >= SPREAD_PLAY_MAX) {
    return {
      label: "PASS",
      reason: `${reason}|outside_spread_play_v2_cap7`,
      isBestBet: false,
    };
  }
  // Below 2.5: LEAN (or PASS only when magnitude is tiny).
  if (absEdge < SPREAD_PLAY_MIN && absEdge >= 1.0) {
    return {
      label: "LEAN",
      reason: `${reason}|outside_spread_play_v2_cap7`,
      isBestBet: false,
    };
  }
  return {
    label: "PASS",
    reason: `${reason}|outside_spread_play_v2_cap7`,
    isBestBet: false,
  };
}

/** Totals PLAY sat until a new unused holdout greens (Ryan lock 2026-09-03). */
function applyTotalsPlaySat(
  label: ActionLabel,
  reason: string,
): { label: ActionLabel; reason: string; isBestBet: boolean } {
  if (TOTAL_PLAY_ENABLED) {
    return { label, reason, isBestBet: label === "BEST VALUE" };
  }
  if (label !== "PLAY" && label !== "BEST VALUE") {
    return { label, reason, isBestBet: false };
  }
  return {
    label: "LEAN",
    reason: `${reason}|totals_play_sat`,
    isBestBet: false,
  };
}

export function decideSide(args: {
  fairSpreadHome: number | null | undefined;
  marketSpreadHome: number | null | undefined;
  week?: number | null;
  coverProb?: number | null;
  openingSpreadHome?: number | null;
  closingSpreadHome?: number | null;
  homeAbbr?: string;
  awayAbbr?: string;
  confidence?: ConfidenceAssessment;
  priceStillAvailable?: boolean;
  matchupSupport?: boolean;
  liquidityOk?: boolean;
  stayAway?: boolean;
}): DecisionResult {
  const conf = args.confidence ?? assessConfidence();
  const week = args.week ?? null;
  const regime = weekRegime(week);
  const matchupSupport = args.matchupSupport !== false;
  const liquidityOk = args.liquidityOk !== false;
  const mc = assessMarketConfirmation({
    modelFair: args.fairSpreadHome,
    opening: args.openingSpreadHome,
    current: args.marketSpreadHome,
    closing: args.closingSpreadHome,
    likesHomeOrOver:
      args.fairSpreadHome == null || args.marketSpreadHome == null
        ? null
        : args.fairSpreadHome - args.marketSpreadHome < 0,
  });

  if (args.fairSpreadHome == null || args.marketSpreadHome == null) {
    return {
      market: "spread",
      actionLabel: "PASS",
      pointGrade: "PASS",
      edgeMagnitude: 0,
      modelConfidence: conf,
      coverProb: args.coverProb ?? null,
      coverGrade: gradeCoverProb(args.coverProb),
      playTo: null,
      marketConfirmation: mc,
      isBestBet: false,
      modelWarning: false,
      keyNumberCross: false,
      priceStillAvailable: args.priceStillAvailable !== false,
      numericalEdge: false,
      confidenceOk: false,
      reason: "missing_fair_or_market",
      week,
      weekRegime: regime,
      fairLine: args.fairSpreadHome ?? null,
      marketLine: args.marketSpreadHome ?? null,
    };
  }

  const fair = args.fairSpreadHome;
  const market = args.marketSpreadHome;
  const edge = fair - market;
  const absEdge = Math.abs(edge);
  let pointGrade = gradeSidePoints(absEdge, week);
  const coverGrade = gradeCoverProb(args.coverProb);
  let effective = coverWins(pointGrade, coverGrade);
  const keyCross = crossesKeyNumber(fair, market, "spread");
  if (keyCross && pointGrade === "LEAN" && absEdge >= 2.0) {
    if (!coverGrade && pointRank(effective) < pointRank("PLAY")) {
      effective = "PLAY";
    }
    pointGrade = "PLAY";
  }

  const ladder = buildSidePlayToLadder({
    fairSpreadHome: fair,
    marketSpreadHome: market,
    homeAbbr: args.homeAbbr,
    awayAbbr: args.awayAbbr,
    week,
  });
  const pastPlayTo = marketPastPlayTo({
    marketKind: "spread",
    fair,
    market,
    ladder,
  });
  if (pastPlayTo && pointRank(effective) >= pointRank("PLAY")) {
    effective =
      pointRank(pointGrade) < pointRank("PLAY") ? pointGrade : "LEAN";
  }
  const priceOk = args.priceStillAvailable !== false && !pastPlayTo;

  const modelWarning =
    args.coverProb != null && Number(args.coverProb) >= COVER_MODEL_WARNING;
  const numericalEdge = ["LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL"].includes(
    effective,
  );
  const confidenceOk = confidenceOkForPlay(conf);
  const uncertain = majorUncertainty(conf);

  let actionLabel: ActionLabel;
  let reason: string;
  let playTo: PlayToLadder | null = null;

  if (args.stayAway || conf.unresolvedFlags.includes("conflicting_inputs")) {
    actionLabel = "STAY AWAY";
    reason = "conflicting_inputs_or_bad_market";
  } else if (numericalEdge && (uncertain || conf.band === "LOW")) {
    actionLabel = "ALERT";
    reason =
      conf.band === "LOW" && !uncertain
        ? "edge_with_low_confidence"
        : "edge_with_material_uncertainty";
    playTo = ladder;
  } else if (effective === "PASS") {
    actionLabel = "PASS";
    reason = "edge_below_week_threshold";
  } else if (effective === "LEAN") {
    actionLabel = "LEAN";
    reason = pastPlayTo
      ? "mild_edge_watch_list|past_play_to"
      : "mild_edge_watch_list";
    playTo = ladder;
  } else if (numericalEdge && confidenceOk && priceOk) {
    const isBb = evaluateBestBet({
      pointGrade: effective === "EXCEPTIONAL" ? "STRONG PLAY" : effective,
      confidence: conf,
      priceAvailable: priceOk,
      keyNumberCross: keyCross,
      marketConfirmation: mc,
      matchupSupport,
      liquidityOk,
    });
    actionLabel = isBb ? "BEST VALUE" : "PLAY";
    reason = isBb ? "best_bet_strict_cleared" : "play_triple_cleared";
    playTo = ladder;
  } else if (numericalEdge && !priceOk) {
    actionLabel =
      pointRank(pointGrade) >= pointRank("PLAY") ? "ALERT" : "LEAN";
    reason = pastPlayTo
      ? "edge_but_price_gone|past_play_to"
      : "edge_but_price_gone";
    playTo = ladder;
  } else if (numericalEdge && !confidenceOk) {
    actionLabel = "ALERT";
    reason = "edge_but_confidence_insufficient";
    playTo = ladder;
  } else {
    actionLabel = "LEAN";
    reason = "partial_play_requirements";
    playTo = ladder;
  }

  if (
    modelWarning &&
    (actionLabel === "PLAY" ||
      actionLabel === "BEST VALUE" ||
      actionLabel === "LEAN")
  ) {
    reason = `${reason}|model_warning_60pct_plus_ats`;
  }

  const holdout = applySpreadPlayHoldoutBand(actionLabel, absEdge, reason);
  actionLabel = holdout.label;
  reason = holdout.reason;

  return {
    market: "spread",
    actionLabel,
    pointGrade,
    edgeMagnitude: Math.round(absEdge * 1000) / 1000,
    modelConfidence: conf,
    coverProb: args.coverProb ?? null,
    coverGrade,
    playTo,
    marketConfirmation: mc,
    isBestBet: holdout.isBestBet,
    modelWarning,
    keyNumberCross: keyCross,
    priceStillAvailable: priceOk,
    numericalEdge,
    confidenceOk,
    reason,
    week,
    weekRegime: regime,
    fairLine: fair,
    marketLine: market,
  };
}

export function decideTotal(args: {
  fairTotal: number | null | undefined;
  marketTotal: number | null | undefined;
  week?: number | null;
  overProb?: number | null;
  openingTotal?: number | null;
  closingTotal?: number | null;
  confidence?: ConfidenceAssessment;
  priceStillAvailable?: boolean;
  matchupSupport?: boolean;
  liquidityOk?: boolean;
  stayAway?: boolean;
}): DecisionResult {
  const conf = args.confidence ?? assessConfidence();
  const week = args.week ?? null;
  const regime = weekRegime(week);
  const matchupSupport = args.matchupSupport !== false;
  const liquidityOk = args.liquidityOk !== false;
  const mc = assessMarketConfirmation({
    modelFair: args.fairTotal,
    opening: args.openingTotal,
    current: args.marketTotal,
    closing: args.closingTotal,
    likesHomeOrOver:
      args.fairTotal == null || args.marketTotal == null
        ? null
        : args.fairTotal - args.marketTotal > 0,
  });

  if (args.fairTotal == null || args.marketTotal == null) {
    return {
      market: "total",
      actionLabel: "PASS",
      pointGrade: "PASS",
      edgeMagnitude: 0,
      modelConfidence: conf,
      coverProb: args.overProb ?? null,
      coverGrade: gradeCoverProb(args.overProb),
      playTo: null,
      marketConfirmation: mc,
      isBestBet: false,
      modelWarning: false,
      keyNumberCross: false,
      priceStillAvailable: args.priceStillAvailable !== false,
      numericalEdge: false,
      confidenceOk: false,
      reason: "missing_fair_or_market",
      week,
      weekRegime: regime,
      fairLine: args.fairTotal ?? null,
      marketLine: args.marketTotal ?? null,
    };
  }

  const fair = args.fairTotal;
  const market = args.marketTotal;
  const edge = fair - market;
  const absEdge = Math.abs(edge);
  const pointGrade = gradeTotalPoints(absEdge, week);
  let coverSideProb = args.overProb ?? null;
  if (args.overProb != null && edge < 0) {
    coverSideProb = 1 - Number(args.overProb);
  }
  const coverGrade = gradeCoverProb(coverSideProb);
  let effective = coverWins(pointGrade, coverGrade);
  const keyCross = crossesKeyNumber(fair, market, "total");

  const ladder = buildTotalPlayToLadder({
    fairTotal: fair,
    marketTotal: market,
    week,
  });
  const pastPlayTo = marketPastPlayTo({
    marketKind: "total",
    fair,
    market,
    ladder,
  });
  if (pastPlayTo && pointRank(effective) >= pointRank("PLAY")) {
    effective =
      pointRank(pointGrade) < pointRank("PLAY") ? pointGrade : "LEAN";
  }
  const priceOk = args.priceStillAvailable !== false && !pastPlayTo;

  const modelWarning =
    coverSideProb != null && Number(coverSideProb) >= COVER_MODEL_WARNING;
  const numericalEdge = ["LEAN", "PLAY", "STRONG PLAY", "EXCEPTIONAL"].includes(
    effective,
  );
  const confidenceOk = confidenceOkForPlay(conf);
  const uncertain =
    majorUncertainty(conf) && conf.score < CONFIDENCE_PLAY_MIN;

  let actionLabel: ActionLabel;
  let reason: string;
  let playTo: PlayToLadder | null = null;

  if (args.stayAway || conf.unresolvedFlags.includes("conflicting_inputs")) {
    actionLabel = "STAY AWAY";
    reason = "conflicting_inputs_or_bad_market";
  } else if (numericalEdge && (uncertain || conf.band === "LOW")) {
    actionLabel = "ALERT";
    reason =
      conf.band === "LOW"
        ? "edge_with_low_confidence"
        : "edge_with_material_uncertainty";
    playTo = ladder;
  } else if (effective === "PASS") {
    actionLabel = "PASS";
    reason = "edge_below_total_threshold";
  } else if (effective === "LEAN") {
    actionLabel = "LEAN";
    reason = pastPlayTo
      ? "mild_edge_watch_list|past_play_to"
      : "mild_edge_watch_list";
    playTo = ladder;
  } else if (numericalEdge && confidenceOk && priceOk) {
    const isBb = evaluateBestBet({
      pointGrade: effective === "EXCEPTIONAL" ? "STRONG PLAY" : effective,
      confidence: conf,
      priceAvailable: priceOk,
      keyNumberCross: keyCross,
      marketConfirmation: mc,
      matchupSupport,
      liquidityOk,
    });
    actionLabel = isBb ? "BEST VALUE" : "PLAY";
    reason = isBb ? "best_bet_strict_cleared" : "play_triple_cleared";
    playTo = ladder;
  } else if (numericalEdge && !priceOk) {
    actionLabel =
      pointRank(pointGrade) >= pointRank("PLAY") ? "ALERT" : "LEAN";
    reason = pastPlayTo
      ? "edge_but_price_gone|past_play_to"
      : "edge_but_price_gone";
    playTo = ladder;
  } else if (numericalEdge && !confidenceOk) {
    actionLabel = "ALERT";
    reason = "edge_but_confidence_insufficient";
    playTo = ladder;
  } else {
    actionLabel = "LEAN";
    reason = "partial_play_requirements";
    playTo = ladder;
  }

  const totalsSat = applyTotalsPlaySat(actionLabel, reason);
  actionLabel = totalsSat.label;
  reason = totalsSat.reason;

  return {
    market: "total",
    actionLabel,
    pointGrade,
    edgeMagnitude: Math.round(absEdge * 1000) / 1000,
    modelConfidence: conf,
    coverProb: coverSideProb,
    coverGrade,
    playTo,
    marketConfirmation: mc,
    isBestBet: totalsSat.isBestBet,
    modelWarning,
    keyNumberCross: keyCross,
    priceStillAvailable: priceOk,
    numericalEdge,
    confidenceOk,
    reason,
    week,
    weekRegime: regime,
    fairLine: fair,
    marketLine: market,
  };
}

export function decideGame(args: {
  week: number | null | undefined;
  fairSpreadHome: number | null | undefined;
  marketSpreadHome: number | null | undefined;
  fairTotal: number | null | undefined;
  marketTotal: number | null | undefined;
  homeAbbr?: string;
  awayAbbr?: string;
  coverProb?: number | null;
  overProb?: number | null;
  openingSpreadHome?: number | null;
  openingTotal?: number | null;
  closingSpreadHome?: number | null;
  closingTotal?: number | null;
  confidence?: ConfidenceAssessment;
  priceStillAvailableSpread?: boolean;
  priceStillAvailableTotal?: boolean;
  matchupSupport?: boolean;
  liquidityOk?: boolean;
  stayAway?: boolean;
}): {
  doctrine: string;
  week: number | null;
  weekRegime: WeekRegime;
  spread: DecisionResult;
  total: DecisionResult;
  edgeMagnitudeSpread: number;
  edgeMagnitudeTotal: number;
  modelConfidence: ConfidenceAssessment;
  actionLabelSpread: ActionLabel;
  actionLabelTotal: ActionLabel;
} {
  const conf = args.confidence ?? assessConfidence();
  const week = args.week ?? null;
  const spread = decideSide({
    fairSpreadHome: args.fairSpreadHome,
    marketSpreadHome: args.marketSpreadHome,
    week,
    coverProb: args.coverProb,
    openingSpreadHome: args.openingSpreadHome,
    closingSpreadHome: args.closingSpreadHome,
    homeAbbr: args.homeAbbr,
    awayAbbr: args.awayAbbr,
    confidence: conf,
    priceStillAvailable: args.priceStillAvailableSpread,
    matchupSupport: args.matchupSupport,
    liquidityOk: args.liquidityOk,
    stayAway: args.stayAway,
  });
  const total = decideTotal({
    fairTotal: args.fairTotal,
    marketTotal: args.marketTotal,
    week,
    overProb: args.overProb,
    openingTotal: args.openingTotal,
    closingTotal: args.closingTotal,
    confidence: conf,
    priceStillAvailable: args.priceStillAvailableTotal,
    matchupSupport: args.matchupSupport,
    liquidityOk: args.liquidityOk,
    stayAway: args.stayAway,
  });
  return {
    doctrine: "We bet prices, not teams.",
    week,
    weekRegime: weekRegime(week),
    spread,
    total,
    edgeMagnitudeSpread: spread.edgeMagnitude,
    edgeMagnitudeTotal: total.edgeMagnitude,
    modelConfidence: conf,
    actionLabelSpread: spread.actionLabel,
    actionLabelTotal: total.actionLabel,
  };
}

/** Serialize DecisionResult for Edge Board / API passthrough (snake_case). */
export function decisionResultToApi(d: DecisionResult): Record<string, unknown> {
  return {
    market: d.market,
    action_label: d.actionLabel,
    point_grade: d.pointGrade,
    edge_magnitude: d.edgeMagnitude,
    model_confidence: {
      score: d.modelConfidence.score,
      band: d.modelConfidence.band,
      factors: d.modelConfidence.factors,
      unresolved_flags: d.modelConfidence.unresolvedFlags,
    },
    cover_prob: d.coverProb,
    cover_grade: d.coverGrade,
    play_to: d.playTo
      ? {
          side_or_total: d.playTo.sideOrTotal,
          play_to: d.playTo.playTo,
          lean_to: d.playTo.leanTo,
          pass_from: d.playTo.passFrom,
          fair_line: d.playTo.fairLine,
          market_line: d.playTo.marketLine,
          edge_points: d.playTo.edgePoints,
          notes: d.playTo.notes,
        }
      : null,
    market_confirmation: {
      model_fair: d.marketConfirmation.modelFair,
      opening: d.marketConfirmation.opening,
      current: d.marketConfirmation.current,
      closing: d.marketConfirmation.closing,
      confirms_thesis: d.marketConfirmation.confirmsThesis,
      weakens_thesis: d.marketConfirmation.weakensThesis,
      note: d.marketConfirmation.note,
    },
    is_best_bet: d.isBestBet,
    model_warning: d.modelWarning,
    key_number_cross: d.keyNumberCross,
    price_still_available: d.priceStillAvailable,
    numerical_edge: d.numericalEdge,
    confidence_ok: d.confidenceOk,
    reason: d.reason,
    week: d.week,
    week_regime: d.weekRegime,
    fair_line: d.fairLine,
    market_line: d.marketLine,
  };
}
